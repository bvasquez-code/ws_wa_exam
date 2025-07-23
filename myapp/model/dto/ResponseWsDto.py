import logging
from myapp.model.dto.ResponseAdditionalDto import ResponseAdditionalDto

class ResponseWsDto:
    def __init__(self):
        self.Status = None
        self.Message = None
        self.Data = None
        self.ErrorStatus = False
        self.ErrorID = 0
        self.DataAdditional = []
        self.ok()  # Configura el estado inicial como "OK"

    def ok(self):
        """Configura la respuesta como correcta."""
        self.Status = "200"
        self.Message = "operation performed successfully"
        self.ErrorStatus = False

    def error(self, message="Error : An unexpected error occurred"):
        """Configura la respuesta como error."""
        self.Status = "500"
        self.Message = message
        self.ErrorStatus = True

    @classmethod
    def from_data(cls, data):
        """Constructor alternativo que recibe datos."""
        instance = cls()
        instance.Data = data
        instance.ok()
        return instance

    @classmethod
    def from_exception(cls, exception: Exception):
        """Constructor alternativo que recibe una excepción."""
        instance = cls()
        logging.error(str(exception), exc_info=True)
        instance.Data = exception
        instance.error(str(exception))
        return instance

    @classmethod
    def from_message(cls, message: str):
        """Constructor alternativo que recibe un mensaje."""
        instance = cls()
        instance.Message = message
        instance.ok()
        return instance

    def add_response_additional(self, name, data):
        """Agrega un ResponseAdditionalDto a la lista DataAdditional."""
        self.DataAdditional.append(ResponseAdditionalDto(name, data))

    def ok_response(self, data):
        """Método fluido para establecer una respuesta correcta con datos."""
        self.ok()
        self.Data = data
        return self

    def error_response(self, exception: Exception):
        """Método fluido para establecer una respuesta de error a partir de una excepción."""
        logging.error(str(exception), exc_info=True)
        self.Data = exception
        self.error(str(exception))
        return self
