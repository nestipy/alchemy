from datetime import datetime
from typing import List, Optional
from pydantic import Field
from sqlalchemy import DateTime, String, func, Integer, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, declarative_base, relationship

from nestipy_alchemy import sqlalchemy_to_pydantic

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255))
    password: Mapped[str] = mapped_column(String(255))
    videos: Mapped[List["Video"]] = relationship("Video", back_populates="user")
    comments: Mapped[List["Comment"]] = relationship("Comment", back_populates="user")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"User(id={self.id!r}, name={self.name!r}, email={self.email!r})"


class Video(Base):
    __tablename__ = "videos"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    url: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(String(255))
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    user: Mapped[User] = relationship("User", back_populates="videos")
    comments: Mapped[List["Comment"]] = relationship("Comment", back_populates="video")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class Comment(Base):
    __tablename__ = "comments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    comment: Mapped[str] = mapped_column(Text)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    user: Mapped[User] = relationship("User", back_populates="comments")
    video_id: Mapped[int] = mapped_column(Integer, ForeignKey("videos.id"))
    video: Mapped[Video] = relationship("Video", back_populates="comments")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


UserModel = sqlalchemy_to_pydantic(User)
VideoModel = sqlalchemy_to_pydantic(Video)
CommentModel = sqlalchemy_to_pydantic(Comment)


class VideoWithRelation(VideoModel):
    comments: List["CommentWithRelation"] = Field(default=[])
    user: Optional[UserModel] = Field(default=None)


class UserWithRelation(UserModel):
    videos: Optional[List[VideoWithRelation]] = Field(default=[])
    comments: Optional[List["CommentWithRelation"] ]= Field(default=[])


class CommentWithRelation(CommentModel):
    user: Optional[UserModel] = Field(default=None)
