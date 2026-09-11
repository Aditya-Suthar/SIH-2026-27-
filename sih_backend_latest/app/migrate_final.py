"""Apply prior AI migrations and create additive support tables before app workers."""
from .database import engine
from .migrate_ai_prompt3 import upgrade as prior_upgrade
from .models import Base

def upgrade(bind):
    prior_upgrade(bind)
    Base.metadata.create_all(bind)

if __name__ == '__main__':
    upgrade(engine)
    print('Sahas schema ready.')
