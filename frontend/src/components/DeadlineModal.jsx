import React from 'react';
import { Plus } from 'lucide-react';
import { Button } from './ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from './ui/dialog';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Textarea } from './ui/textarea';
import { Checkbox } from './ui/checkbox';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';

const DeadlineModal = ({ isOpen, onOpenChange, editingDeadline, formData, setFormData, onSave, onCancel, onTriggerClick }) => {
  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogTrigger asChild>
        <Button
          onClick={onTriggerClick}
          className="bg-slate-700 hover:bg-slate-800 dark:bg-slate-600 dark:hover:bg-slate-500 text-white px-6 py-3 rounded-lg shadow-md hover:shadow-lg transition-all duration-200 hover:scale-105"
        >
          <Plus className="w-5 h-5 mr-2" />
          Add Deadline
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="text-slate-700 dark:text-slate-300">
            {editingDeadline ? 'Edit Deadline' : 'Add New Deadline'}
          </DialogTitle>
        </DialogHeader>
        <div className="space-y-4 mt-4">
          <div>
            <Label htmlFor="name" className="text-slate-700 dark:text-slate-300">Name</Label>
            <Input
              id="name"
              value={formData.name}
              onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
              placeholder="Enter person's name"
              className="mt-1"
            />
          </div>
          <div>
            <Label htmlFor="task" className="text-slate-700 dark:text-slate-300">Task / Description</Label>
            <Textarea
              id="task"
              value={formData.task}
              onChange={(e) => setFormData(prev => ({ ...prev, task: e.target.value }))}
              placeholder="What needs to be done?"
              className="mt-1 min-h-[80px]"
            />
          </div>
          <div>
            <Label htmlFor="dueDate" className="text-slate-700 dark:text-slate-300">Due Date & Time (Moscow)</Label>
            <Input
              id="dueDate"
              type="datetime-local"
              value={formData.dueDate}
              onChange={(e) => setFormData(prev => ({ ...prev, dueDate: e.target.value }))}
              className="mt-1"
            />
          </div>

          <div>
            <Label htmlFor="daysNeeded" className="text-slate-700 dark:text-slate-300">Days needed (optional)</Label>
            <Input
              id="daysNeeded"
              type="number"
              min="1"
              max="365"
              value={formData.daysNeeded || ''}
              onChange={(e) => setFormData(prev => ({ ...prev, daysNeeded: e.target.value }))}
              placeholder="How many days to complete?"
              className="mt-1"
            />
          </div>

          {/* Recurring Options */}
          <div className="space-y-3 border-t pt-4">
            <div className="flex items-center space-x-2">
              <Checkbox
                id="isRecurring"
                checked={formData.isRecurring}
                onCheckedChange={(checked) => setFormData(prev => ({ ...prev, isRecurring: checked }))}
              />
              <Label htmlFor="isRecurring" className="text-slate-700 dark:text-slate-300">
                Make temporary (recurring)
              </Label>
            </div>

            {formData.isRecurring && (
              <div>
                <Label htmlFor="intervalDays" className="text-slate-700 dark:text-slate-300">Period (days)</Label>
                <Select
                  value={formData.intervalDays}
                  onValueChange={(value) => setFormData(prev => ({ ...prev, intervalDays: value }))}
                >
                  <SelectTrigger className="mt-1">
                    <SelectValue placeholder="Select period" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="7">7 days (week)</SelectItem>
                    <SelectItem value="14">14 days (2 weeks)</SelectItem>
                    <SelectItem value="30">30 days (month)</SelectItem>
                    <SelectItem value="custom">Custom period...</SelectItem>
                  </SelectContent>
                </Select>

                {formData.intervalDays === 'custom' && (
                  <Input
                    type="number"
                    min="1"
                    placeholder="Enter number of days"
                    className="mt-2"
                    value={formData.customDays}
                    onChange={(e) => setFormData(prev => ({ ...prev, customDays: e.target.value }))}
                  />
                )}
              </div>
            )}
          </div>

          <div className="flex gap-3 pt-4">
            <Button
              onClick={onSave}
              className="flex-1 bg-blue-600 hover:bg-blue-700 text-white disabled:bg-slate-600 disabled:text-slate-400 disabled:opacity-50"
              disabled={!formData.name.trim() || !formData.task.trim() || !formData.dueDate ||
                       (formData.isRecurring && formData.intervalDays === 'custom' && !formData.customDays.trim())}
            >
              {editingDeadline ? 'Save Changes' : 'Add Deadline'}
            </Button>
            <Button
              onClick={onCancel}
              variant="outline"
              className="flex-1"
            >
              Cancel
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default DeadlineModal;
