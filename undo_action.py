import sys
import os
from PyQt5.QtWidgets import QUndoCommand, QUndoStack, QUndoGroup
from common import StackWidget

class UndoGroupStack(StackWidget):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.undo_group=QUndoGroup(self)
        self.undo_stack_correspond={}

    def addWidget(self, widget, obj=None, switch=True):
        result=super().addWidget(widget, obj, switch)
        if result:
            self.undo_group.setActiveStack(self.undo_stack_correspond[obj])
        else:
            new=QUndoStack(self)
            self.undo_group.addStack(new)
            self.undo_stack_correspond[obj]=new
        if switch:
            self.undo_group.setActiveStack(self.undo_stack_correspond[obj])
        return result
    
    def push(self,command:QUndoCommand):
        self.undo_group.activeStack().push(command)

    def redo(self):
        print("redo")
        self.undo_group.activeStack().redo()

    def undo(self):
        print("undo")
        self.undo_group.activeStack().undo()

class AddComponentButton(QUndoCommand):
    def __init__(self):
        super().__init__()
    
    def redo(self):
        return super().redo()
    
    def undo(self):
        return super().undo()
    
class DelComponentButton(QUndoCommand):
    def __init__(self):
        super().__init__()
    
    def redo(self):
        return super().redo()
    
    def undo(self):
        return super().undo()
    
class AddLayer(QUndoCommand):
    def __init__(self):
        super().__init__()
    
    def redo(self):
        return super().redo()
    
    def undo(self):
        return super().undo()
    
class DelLayer(QUndoCommand):
    def __init__(self):
        super().__init__()
    
    def redo(self):
        return super().redo()
    
    def undo(self):
        return super().undo()
    
class ToggleVisibility(QUndoCommand):
    def __init__(self):
        super().__init__()
    
    def redo(self):
        return super().redo()
    
    def undo(self):
        return super().undo()

class ValueChange(QUndoCommand):
    def __init__(self):
        super().__init__()
    
    def redo(self):
        return super().redo()
    
    def undo(self):
        return super().undo()