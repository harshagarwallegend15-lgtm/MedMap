from abc import ABC, abstractmethod
from app.services.ai.schemas import ProcessIntakeRequest, StructuredClinicalOutput


class BaseAIProvider(ABC):
    @abstractmethod
    def process_case(self, request: ProcessIntakeRequest) -> StructuredClinicalOutput:
        pass
