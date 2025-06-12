"""
Custom exceptions for the plugin system
"""


class PluginError(Exception):
    """Base exception for plugin-related errors"""
    pass


class PluginNotFoundError(PluginError):
    """Raised when a plugin is not found"""
    pass


class PluginAlreadyRegisteredError(PluginError):
    """Raised when trying to register a plugin that's already registered"""
    pass


class PluginDependencyError(PluginError):
    """Raised when plugin dependencies are not met"""
    pass


class PluginValidationError(PluginError):
    """Raised when plugin validation fails"""
    pass