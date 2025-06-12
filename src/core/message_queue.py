"""
Message Queue implementation for agent communication
"""
import asyncio
import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
import uuid


class MessagePriority(Enum):
    """Message priority levels"""
    LOW = 1
    NORMAL = 5
    HIGH = 8
    CRITICAL = 10


@dataclass
class Message:
    """Message structure for the queue"""
    id: str
    topic: str
    payload: Dict[str, Any]
    timestamp: datetime
    priority: MessagePriority = MessagePriority.NORMAL
    retry_count: int = 0
    max_retries: int = 3
    ttl_seconds: Optional[int] = None
    
    def __lt__(self, other):
        """Compare messages for priority queue ordering"""
        if not isinstance(other, Message):
            return NotImplemented
        # Compare by timestamp if priorities are equal
        if self.priority.value == other.priority.value:
            return self.timestamp < other.timestamp
        return self.priority.value < other.priority.value
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['priority'] = self.priority.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """Create message from dictionary"""
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        data['priority'] = MessagePriority(data['priority'])
        return cls(**data)


class MessageQueue:
    """In-memory message queue with topic-based routing"""
    
    def __init__(self):
        self.topics: Dict[str, asyncio.Queue] = {}
        self.subscribers: Dict[str, List[Callable]] = {}
        self.dead_letter_queue: asyncio.Queue = asyncio.Queue()
        self._running = False
        self._tasks: List[asyncio.Task] = []
        
    async def initialize(self):
        """Initialize the message queue"""
        self._running = True
        # Start background tasks
        self._tasks.append(asyncio.create_task(self._process_dead_letters()))
        self._tasks.append(asyncio.create_task(self._cleanup_expired_messages()))
        
    async def shutdown(self):
        """Shutdown the message queue"""
        self._running = False
        # Cancel all tasks
        for task in self._tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
    
    async def publish(self, payload: Dict[str, Any], topic: str = "default",
                     priority: MessagePriority = MessagePriority.NORMAL,
                     ttl_seconds: Optional[int] = None):
        """Publish a message to a topic"""
        message = Message(
            id=str(uuid.uuid4()),
            topic=topic,
            payload=payload,
            timestamp=datetime.now(timezone.utc),
            priority=priority,
            ttl_seconds=ttl_seconds
        )
        
        # Create topic queue if doesn't exist
        if topic not in self.topics:
            self.topics[topic] = asyncio.PriorityQueue()
        
        # Add to queue with priority
        await self.topics[topic].put((-message.priority.value, message))
        
        # Notify subscribers
        await self._notify_subscribers(topic, message)
        
        return message.id
    
    async def subscribe(self, topic: str, callback: Callable):
        """Subscribe to a topic with a callback"""
        if topic not in self.subscribers:
            self.subscribers[topic] = []
            
        self.subscribers[topic].append(callback)
        
        # Create topic queue if doesn't exist
        if topic not in self.topics:
            self.topics[topic] = asyncio.PriorityQueue()
    
    async def unsubscribe(self, topic: str, callback: Callable):
        """Unsubscribe from a topic"""
        if topic in self.subscribers and callback in self.subscribers[topic]:
            self.subscribers[topic].remove(callback)
            
            # Remove topic if no subscribers
            if not self.subscribers[topic]:
                del self.subscribers[topic]
    
    async def consume(self, topic: str, timeout: Optional[float] = None) -> Optional[Message]:
        """Consume a message from a topic"""
        if topic not in self.topics:
            return None
        
        try:
            if timeout:
                priority, message = await asyncio.wait_for(
                    self.topics[topic].get(),
                    timeout=timeout
                )
            else:
                priority, message = await self.topics[topic].get()
            
            # Check if message expired
            if message.ttl_seconds:
                age = (datetime.now(timezone.utc) - message.timestamp).total_seconds()
                if age > message.ttl_seconds:
                    # Message expired, move to dead letter queue
                    await self.dead_letter_queue.put(message)
                    return None
            
            return message
            
        except asyncio.TimeoutError:
            return None
    
    async def acknowledge(self, message_id: str):
        """Acknowledge message processing (for future persistence)"""
        # In-memory queue doesn't need acknowledgment
        # This is a placeholder for future persistent queue implementation
        pass
    
    async def reject(self, message: Message, requeue: bool = True):
        """Reject a message, optionally requeuing it"""
        if requeue and message.retry_count < message.max_retries:
            # Increment retry count and requeue
            message.retry_count += 1
            await self.publish(
                payload=message.payload,
                topic=message.topic,
                priority=MessagePriority(max(1, message.priority.value - 1))  # Lower priority
            )
        else:
            # Move to dead letter queue
            await self.dead_letter_queue.put(message)
    
    async def get_queue_stats(self, topic: Optional[str] = None) -> Dict[str, Any]:
        """Get statistics about the queue(s)"""
        if topic:
            if topic not in self.topics:
                return {"error": f"Topic {topic} not found"}
            
            return {
                "topic": topic,
                "queue_size": self.topics[topic].qsize(),
                "subscribers": len(self.subscribers.get(topic, [])),
                "dead_letters": self.dead_letter_queue.qsize()
            }
        else:
            # Get stats for all topics
            stats = {
                "total_topics": len(self.topics),
                "total_subscribers": sum(len(subs) for subs in self.subscribers.values()),
                "dead_letters": self.dead_letter_queue.qsize(),
                "topics": {}
            }
            
            for topic_name, queue in self.topics.items():
                stats["topics"][topic_name] = {
                    "queue_size": queue.qsize(),
                    "subscribers": len(self.subscribers.get(topic_name, []))
                }
            
            return stats
    
    async def purge_topic(self, topic: str):
        """Remove all messages from a topic"""
        if topic in self.topics:
            # Create new queue to replace old one
            self.topics[topic] = asyncio.PriorityQueue()
    
    async def _notify_subscribers(self, topic: str, message: Message):
        """Notify all subscribers of a topic"""
        if topic not in self.subscribers:
            return
        
        # Create tasks for all callbacks
        tasks = []
        for callback in self.subscribers[topic]:
            tasks.append(asyncio.create_task(self._safe_callback(callback, message)))
        
        # Wait for all callbacks to complete
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _safe_callback(self, callback: Callable, message: Message):
        """Safely execute a callback"""
        try:
            result = callback(message)
            if asyncio.iscoroutine(result):
                await result
        except Exception as e:
            # Log error but don't crash
            # In production, this would be logged properly
            pass
    
    async def _process_dead_letters(self):
        """Process dead letter queue"""
        while self._running:
            try:
                # Process dead letters every 60 seconds
                message = await asyncio.wait_for(
                    self.dead_letter_queue.get(),
                    timeout=60.0
                )
                
                # In production, dead letters would be:
                # - Logged for analysis
                # - Potentially saved to persistent storage
                # - Alerted on if they exceed threshold
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                # Log error
                pass
    
    async def _cleanup_expired_messages(self):
        """Clean up expired messages from queues"""
        while self._running:
            try:
                await asyncio.sleep(300)  # Run every 5 minutes
                
                for topic, queue in self.topics.items():
                    # Check messages for expiration
                    temp_messages = []
                    
                    # Drain queue
                    while not queue.empty():
                        try:
                            priority, message = queue.get_nowait()
                            
                            # Check if expired
                            if message.ttl_seconds:
                                age = (datetime.now(timezone.utc) - message.timestamp).total_seconds()
                                if age > message.ttl_seconds:
                                    await self.dead_letter_queue.put(message)
                                    continue
                            
                            temp_messages.append((priority, message))
                        except asyncio.QueueEmpty:
                            break
                    
                    # Re-add non-expired messages
                    for item in temp_messages:
                        await queue.put(item)
                        
            except Exception as e:
                # Log error
                pass


class MessageBus:
    """High-level message bus for agent communication"""
    
    def __init__(self, message_queue: MessageQueue):
        self.message_queue = message_queue
        self.request_handlers: Dict[str, Callable] = {}
        self.pending_requests: Dict[str, asyncio.Future] = {}
        
    async def request(self, topic: str, payload: Dict[str, Any], 
                     timeout: float = 30.0) -> Optional[Dict[str, Any]]:
        """Send a request and wait for response"""
        request_id = str(uuid.uuid4())
        
        # Create future for response
        future = asyncio.Future()
        self.pending_requests[request_id] = future
        
        # Publish request
        await self.message_queue.publish(
            payload={
                "request_id": request_id,
                "data": payload
            },
            topic=f"request.{topic}",
            priority=MessagePriority.HIGH
        )
        
        try:
            # Wait for response
            response = await asyncio.wait_for(future, timeout=timeout)
            return response
        except asyncio.TimeoutError:
            return None
        finally:
            # Clean up
            self.pending_requests.pop(request_id, None)
    
    async def respond(self, request_id: str, response: Dict[str, Any]):
        """Send a response to a request"""
        await self.message_queue.publish(
            payload={
                "request_id": request_id,
                "response": response
            },
            topic="responses",
            priority=MessagePriority.HIGH
        )
    
    async def handle_request(self, topic: str, handler: Callable):
        """Register a request handler"""
        self.request_handlers[topic] = handler
        
        # Subscribe to request topic
        async def process_request(message: Message):
            request_id = message.payload.get("request_id")
            data = message.payload.get("data", {})
            
            try:
                # Call handler
                response = await handler(data)
                
                # Send response
                await self.respond(request_id, response)
            except Exception as e:
                # Send error response
                await self.respond(request_id, {
                    "error": str(e),
                    "success": False
                })
        
        await self.message_queue.subscribe(f"request.{topic}", process_request)
    
    async def initialize(self):
        """Initialize the message bus"""
        # Subscribe to responses
        async def process_response(message: Message):
            request_id = message.payload.get("request_id")
            response = message.payload.get("response")
            
            if request_id in self.pending_requests:
                self.pending_requests[request_id].set_result(response)
        
        await self.message_queue.subscribe("responses", process_response)