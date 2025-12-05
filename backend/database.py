# [advice from AI] 데이터베이스 설정 및 초기화
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from backend.config import get_settings


class Base(DeclarativeBase):
    """SQLAlchemy Base 클래스"""
    pass


# 엔진 및 세션 설정
_engine = None
_async_session = None


def get_engine():
    """비동기 엔진 반환"""
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(
            f"sqlite+aiosqlite:///{settings.db_path}",
            echo=False,
        )
    return _engine


def get_session_maker():
    """세션 메이커 반환"""
    global _async_session
    if _async_session is None:
        _async_session = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _async_session


async def get_db():
    """의존성 주입용 세션 생성기"""
    async_session = get_session_maker()
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """데이터베이스 테이블 초기화"""
    from backend.models.job import Job  # 모델 import
    
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    print("✅ 데이터베이스가 초기화되었습니다.")

