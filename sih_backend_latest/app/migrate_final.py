"""Apply the complete additive schema before app workers."""
from .database import engine
from .migrate_questionnaire_v2 import upgrade as questionnaire_upgrade

def upgrade(bind):
    questionnaire_upgrade(bind)

if __name__ == '__main__':
    upgrade(engine)
    print('Sahas schema ready.')
