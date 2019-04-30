from .normal import Normal_Command
from .freecategory import FreeCategory
from .staff import Staff_Command
from .level import Level
from .events import Events
from .categoryindex import Category_Index
from .categoryrecover import Category_recover
from .botowner import Bot_Owner_Command
from .rolepanel import Role_panel
from .board import DiscussionBoard

def cogs(bot):
    bot.add_cog(Normal_Command(bot, '普通のコマンド'))
    bot.add_cog(Category_Index(bot, 'カテゴリインデックス'))
    bot.add_cog(Bot_Owner_Command(bot, 'BOTオーナー用コマンド'))
    bot.add_cog(Staff_Command(bot, 'スタッフ用コマンド'))
    bot.add_cog(Role_panel(bot, '役職パネル'))
    bot.add_cog(FreeCategory(bot,'自由チャンネル編集コマンド'))
    bot.add_cog(Category_recover(bot, 'カテゴリーリカバリー'))
    bot.add_cog(Events(bot, '参加・退出通知、VC通知'))
    bot.add_cog(Level(bot, 'レベル機能'))
    bot.add_cog(DiscussionBoard(bot, '掲示板機能'))