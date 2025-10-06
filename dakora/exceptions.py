class DakoraError(Exception): pass
class TemplateNotFound(DakoraError): pass
class ValidationError(DakoraError): pass
class RenderError(DakoraError): pass

class LLMError(DakoraError): pass
class APIKeyError(LLMError): pass
class RateLimitError(LLMError): pass
class ModelNotFoundError(LLMError): pass