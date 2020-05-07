from .board import DiscussionBoard
from .botowner import Bot_Owner_Command
from .categoryindex import Category_Index
from .categoryrecover import Category_recover
from .events import Events
from .freecategory import FreeCategory
from .level import Level
from .message_count import Message_count
from .normal import Normal_Command
from .rolesave import Role_save
from .staff import Staff_Command
from .ticket import Ticket


def cogs(bot):
    bot.add_cog(Normal_Command(bot, '普通のコマンド'))
    bot.add_cog(Category_Index(bot, 'カテゴリインデックス'))
    bot.add_cog(Bot_Owner_Command(bot, 'BOTオーナー用コマンド'))
    bot.add_cog(Staff_Command(bot, 'スタッフ用コマンド'))
    bot.add_cog(FreeCategory(bot, '自由チャンネル編集コマンド'))
    bot.add_cog(Category_recover(bot, 'カテゴリーリカバリー'))
    bot.add_cog(Events(bot, '参加・退出通知、VC通知'))
    bot.add_cog(Level(bot, 'レベル機能'))
    bot.add_cog(DiscussionBoard(bot, '掲示板機能'))
    bot.add_cog(Role_save(bot, '役職セーブ'))
    bot.add_cog(Message_count(bot, 'メッセージカウント'))
    bot.add_cog(Ticket(bot, 'トラブルチケット'))
