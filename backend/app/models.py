from sqlalchemy import Column, Integer, String, DateTime, JSON, Text, ForeignKey, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base

task_images = Table(
    'task_images',
    Base.metadata,
    Column('task_id', Integer, ForeignKey('image_tasks.id')),
    Column('image_hash', String, ForeignKey('reference_images.hash'))
)

class ImageTask(Base):
    __tablename__ = "image_tasks"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String, unique=True, index=True) # UUID
    prompt = Column(Text, nullable=False)
    status = Column(String, default="PENDING") # PENDING, RUNNING, COMPLETED, FAILED, CANCELLED
    
    # Result
    image_url = Column(String, nullable=True)
    local_path = Column(String, nullable=True)
    
    # Configuration
    model = Column(String, default="gemini-3-pro-image-preview")
    aspect_ratio = Column(String, default="1:1")
    resolution = Column(String, default="1K")
    
    # Relationships
    reference_images = relationship("ReferenceImage", secondary=task_images, back_populates="tasks")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    error_msg = Column(Text, nullable=True)

class ReferenceImage(Base):
    __tablename__ = "reference_images"

    hash = Column(String, primary_key=True, index=True) # SHA-256
    file_path = Column(String, nullable=False)
    url = Column(String, nullable=False)
    mime_type = Column(String, nullable=False)
    original_name = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    tasks = relationship("ImageTask", secondary=task_images, back_populates="reference_images")
