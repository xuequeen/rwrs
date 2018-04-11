"""empty message

Revision ID: 4f91b682ac26
Revises: 75f07d0bb378
Create Date: 2018-04-04 14:49:05.027460

"""
from alembic import op
import sqlalchemy as sa
import sqlalchemy_utils


# revision identifiers, used by Alembic.
revision = '4f91b682ac26'
down_revision = '75f07d0bb378'
branch_labels = None
depends_on = None


def upgrade(engine_name):
    globals()["upgrade_%s" % engine_name]()


def downgrade(engine_name):
    globals()["downgrade_%s" % engine_name]()





def upgrade_():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('rwr_accounts',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('type', sa.Enum('INVASION', 'PACIFIC', name='rwraccounttype'), nullable=False),
    sa.Column('username', sa.String(length=16), nullable=False),
    sa.Column('created_at', sqlalchemy_utils.types.arrow.ArrowType(), nullable=False),
    sa.Column('updated_at', sqlalchemy_utils.types.arrow.ArrowType(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('type_username_idx', 'rwr_accounts', ['type', 'username'], unique=False)
    # ### end Alembic commands ###


def downgrade_():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index('type_username_idx', table_name='rwr_accounts')
    op.drop_table('rwr_accounts')
    # ### end Alembic commands ###


def upgrade_steam_players_count():
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###


def downgrade_steam_players_count():
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###


def upgrade_rwr_account_stats():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('rwr_account_stats',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('leaderboard_position', sa.Integer(), nullable=False),
    sa.Column('xp', sa.Integer(), nullable=False),
    sa.Column('kills', sa.Integer(), nullable=False),
    sa.Column('deaths', sa.Integer(), nullable=False),
    sa.Column('time_played', sa.Integer(), nullable=False),
    sa.Column('longest_kill_streak', sa.Integer(), nullable=False),
    sa.Column('targets_destroyed', sa.Integer(), nullable=False),
    sa.Column('vehicles_destroyed', sa.Integer(), nullable=False),
    sa.Column('soldiers_healed', sa.Integer(), nullable=False),
    sa.Column('teamkills', sa.Integer(), nullable=False),
    sa.Column('distance_moved', sa.Float(), nullable=False),
    sa.Column('shots_fired', sa.Integer(), nullable=False),
    sa.Column('throwables_thrown', sa.Integer(), nullable=False),
    sa.Column('created_at', sqlalchemy_utils.types.arrow.ArrowType(), nullable=False),
    sa.Column('rwr_account_id', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('rwr_account_id_idx', 'rwr_account_stats', ['rwr_account_id'], unique=False)
    # ### end Alembic commands ###


def downgrade_rwr_account_stats():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index('rwr_account_id_idx', table_name='rwr_account_stats')
    op.drop_table('rwr_account_stats')
    # ### end Alembic commands ###


def upgrade_servers_player_count():
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###


def downgrade_servers_player_count():
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###

