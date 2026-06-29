from sqlalchemy.orm import Session

from app.models.document_generation import DocumentGeneration


class DocumentGenerationRepository:
    """Repositorio para acceder a las generaciones guardadas en base de datos."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, document_generation: DocumentGeneration) -> DocumentGeneration:
        """Guarda una nueva generación en la base de datos."""
        self.db.add(document_generation)
        self.db.commit()
        self.db.refresh(document_generation)
        return document_generation

    def get_all(self) -> list[DocumentGeneration]:
        """Obtiene todas las generaciones ordenadas por fecha descendente."""
        return (
            self.db.query(DocumentGeneration)
            .order_by(DocumentGeneration.created_at.desc())
            .all()
        )

    def get_by_id(self, generation_id: int) -> DocumentGeneration | None:
        """Obtiene una generación por su identificador."""
        return (
            self.db.query(DocumentGeneration)
            .filter(DocumentGeneration.id == generation_id)
            .first()
        )

    def delete(self, document_generation: DocumentGeneration) -> None:
        """Elimina una generación existente."""
        self.db.delete(document_generation)
        self.db.commit()