from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import declarative_base
from .database import Base

class BoxOfficeRevenue(Base):
    __tablename__ = "box_office_revenue"

    # Định nghĩa các cột khớp với database quan hệ
    actor_id = Column(Integer, primary_key=True, index=True)
    actor_name = Column(String(255), nullable=False)
    movie = Column(String(255), nullable=False)
    revenue = Column(Float, nullable=False) # Doanh thu phòng vé
class MovieCast(Base):
    __tablename__ = 'movie_cast'
    
    id = Column(Integer, primary_key=True)
    movie_id = Column(String, ForeignKey('box_office_revenue.movie_id'))
    actor_id = Column(String, ForeignKey('actors.actor_id'))

class Actor(Base):
    __tablename__ = 'actors'
    
    actor_id = Column(String, primary_key=True)
    name = Column(String)