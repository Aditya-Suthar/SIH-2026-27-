"""Apply the complete additive schema before app workers."""
from .database import engine
from .migrate_indicator_evidence import upgrade as evidence_upgrade

def upgrade(bind):
    evidence_upgrade(bind)

if __name__ == '__main__':
    upgrade(engine)
    print('Sahas schema ready.')
