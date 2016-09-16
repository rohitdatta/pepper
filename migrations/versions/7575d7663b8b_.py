"""empty message

Revision ID: 7575d7663b8b
Revises: 2ae4701a60b4
Create Date: 2016-09-15 23:10:44.631970

"""

# revision identifiers, used by Alembic.
revision = '7575d7663b8b'
down_revision = '2ae4701a60b4'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('users', sa.Column('time_applied', sa.DateTime(), nullable=True))
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('users', 'time_applied')
    ### end Alembic commands ###
