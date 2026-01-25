"""Notes service for managing admin notes/corrections."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from squishmark.models.db import Note


class NotesService:
    """Service for CRUD operations on notes."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        path: str,
        text: str,
        author: str,
        is_public: bool = False,
    ) -> Note:
        """Create a new note."""
        note = Note(
            path=path,
            text=text,
            author=author,
            is_public=is_public,
        )
        self.session.add(note)
        await self.session.flush()
        await self.session.refresh(note)
        return note

    async def get_by_id(self, note_id: int) -> Note | None:
        """Get a note by ID."""
        result = await self.session.execute(select(Note).where(Note.id == note_id))
        return result.scalar_one_or_none()

    async def get_for_path(
        self,
        path: str,
        include_private: bool = False,
    ) -> list[Note]:
        """Get all notes for a given path."""
        query = select(Note).where(Note.path == path)

        if not include_private:
            query = query.where(Note.is_public.is_(True))

        query = query.order_by(Note.created_at.desc())

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_all(self, limit: int = 100) -> list[Note]:
        """Get all notes, ordered by most recent first."""
        result = await self.session.execute(select(Note).order_by(Note.created_at.desc()).limit(limit))
        return list(result.scalars().all())

    async def update_note(
        self,
        note_id: int,
        text: str | None = None,
        is_public: bool | None = None,
    ) -> Note | None:
        """Update a note."""
        note = await self.get_by_id(note_id)
        if note is None:
            return None

        if text is not None:
            note.text = text
        if is_public is not None:
            note.is_public = is_public

        note.updated_at = datetime.now()
        await self.session.flush()
        await self.session.refresh(note)
        return note

    async def delete(self, note_id: int) -> bool:
        """Delete a note. Returns True if deleted, False if not found."""
        # First check if the note exists
        note = await self.get_by_id(note_id)
        if note is None:
            return False

        await self.session.delete(note)
        await self.session.flush()
        return True
