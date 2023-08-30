# @since 20230617 copied from bbsengine5
class Form(object):
  def __init__(self, title, items, args=None):
    self.items = items
    self.title = title
    self.args = args
  def __len__(self):
    return len(self.items)
  def __getitem__(self, index):
    return self.items[index]
