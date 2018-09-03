"""empty message

Revision ID: 0aea7ac2396b
Revises: 5cd6fe66e980
Create Date: 2018-09-03 16:33:03.083851

"""

# revision identifiers, used by Alembic.
revision = '0aea7ac2396b'
down_revision = '5cd6fe66e980'

from alembic import op
import sqlalchemy as sa


# Add why_hackathon column for application question

def upgrade():
    op.add_column('users', sa.Column('why_hackathon', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('users', 'why_hackathon')
