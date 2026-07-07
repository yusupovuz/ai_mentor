from sqlalchemy import Column,Integer,String,ForeignKey
from sqlalchemy.orm import relationship
from .database import Base

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer,primary_key=True,index=True)
    username = Column(String,unique=True,index=True)
    hashed_password = Column(String)

    messages = relationship('Message',back_populates='owner')

class Message(Base):
    __tablename__ = 'messages'

    id = Column(Integer,primary_key=True,index=True)
    user_question = Column(String)
    ai_reply = Column(String)
    owner_id = Column(Integer,ForeignKey('users.id'))

    owner = relationship('User',back_populates='messages')
