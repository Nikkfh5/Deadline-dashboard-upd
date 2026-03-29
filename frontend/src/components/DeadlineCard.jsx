import React from 'react';
import { Clock, X, Edit3, MoreVertical, Repeat, CheckCircle2 } from 'lucide-react';
import { Button } from './ui/button';
import { Tooltip, TooltipContent, TooltipTrigger } from './ui/tooltip';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from './ui/dropdown-menu';
import { Card } from './ui/card';
import { Badge } from './ui/badge';
import CircularProgress from './CircularProgress';

const truncateText = (text, maxLength = 25) => {
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength) + '...';
};

const DeadlineCard = ({ deadline, timeLeft, progressColor, progressPercentage, isPulsing, onEdit, onDelete, onComplete, onRepeat, isRegularSection }) => {
  const showRepeatButton = deadline.isRecurring && timeLeft.isOverdue;

  return (
    <Card
      key={deadline.id}
      className="relative p-6 bg-card shadow-md hover:shadow-xl hover:ring-2 hover:ring-ring hover:ring-offset-2 hover:ring-offset-background transition-all duration-200 hover:scale-105 cursor-pointer border border-border"
      onClick={() => onEdit(deadline)}
    >
      {/* 3-dot menu */}
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <button
            onClick={(e) => e.stopPropagation()}
            className="absolute -top-2 -right-2 w-6 h-6 bg-slate-600 hover:bg-slate-700 text-white rounded-full flex items-center justify-center text-xs transition-colors duration-200 shadow-md"
          >
            <MoreVertical className="w-3 h-3" />
          </button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-32">
          <DropdownMenuItem
            onClick={(e) => {
              e.stopPropagation();
              onEdit(deadline);
            }}
            className="cursor-pointer"
          >
            <Edit3 className="w-4 h-4 mr-2" />
            Edit
          </DropdownMenuItem>
          {showRepeatButton && (
            <DropdownMenuItem
              onClick={(e) => {
                e.stopPropagation();
                onRepeat(deadline);
              }}
              className="cursor-pointer text-blue-600 focus:text-blue-600"
            >
              <Repeat className="w-4 h-4 mr-2" />
              Repeat
            </DropdownMenuItem>
          )}
          <DropdownMenuItem
            onClick={(e) => {
              e.stopPropagation();
              onComplete(deadline.id);
            }}
            className="cursor-pointer text-green-600 focus:text-green-600"
          >
            <CheckCircle2 className="w-4 h-4 mr-2" />
            Done
          </DropdownMenuItem>
          <DropdownMenuItem
            onClick={(e) => {
              e.stopPropagation();
              onDelete(deadline.id);
            }}
            className="cursor-pointer text-red-600 focus:text-red-600"
          >
            <X className="w-4 h-4 mr-2" />
            Delete
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      {/* Badge for deadline type */}
      <div className="absolute -top-2 -left-2">
        {deadline.isRecurring && !timeLeft.isOverdue && (
          <Badge variant="outline" className="bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 border-blue-300 dark:border-blue-700 text-xs px-2 py-1">
            every {deadline.intervalDays} days
          </Badge>
        )}
        {showRepeatButton && (
          <Badge variant="outline" className="bg-orange-100 dark:bg-orange-900 text-orange-700 dark:text-orange-300 border-orange-300 dark:border-orange-700 text-xs px-2 py-1">
            repeat
          </Badge>
        )}
      </div>

      <div className="flex flex-col items-center space-y-4 mt-4">
        {/* Circular Progress */}
        <CircularProgress
          percentage={progressPercentage}
          color={progressColor}
          isPulsing={isPulsing}
        >
          <Clock className="w-6 h-6 text-muted-foreground mb-1" />
          <div className="text-center">
            <div className="text-xs font-mono text-foreground">
              {timeLeft.isOverdue ? (
                <span className="text-red-600 font-semibold">OVERDUE</span>
              ) : (
                `${timeLeft.days}d ${timeLeft.hours}h`
              )}
            </div>
            <div className="text-xs font-mono text-muted-foreground">
              {timeLeft.isOverdue ? '' : `${timeLeft.minutes}m ${timeLeft.seconds}s`}
            </div>
          </div>
        </CircularProgress>

        {/* Name and Task */}
        <div className="text-center">
          <h3 className="font-semibold text-card-foreground text-lg">{deadline.name}</h3>
          {deadline.task && (
            <Tooltip>
              <TooltipTrigger asChild>
                <p className="text-xs text-muted-foreground mt-1 cursor-help">
                  {truncateText(deadline.task)}
                </p>
              </TooltipTrigger>
              <TooltipContent className="max-w-xs">
                <p>{deadline.task}</p>
              </TooltipContent>
            </Tooltip>
          )}
          <p className="text-xs text-muted-foreground mt-1">
            {new Date(deadline.dueDate).toLocaleDateString('ru-RU', {
              timeZone: 'Europe/Moscow',
              month: 'short',
              day: 'numeric',
              hour: '2-digit',
              minute: '2-digit'
            })} {timeLeft.isOverdue ? 'ago' : 'to go'}
          </p>
        </div>

        {/* Repeat Button for regular section */}
        {showRepeatButton && isRegularSection && (
          <Button
            onClick={(e) => {
              e.stopPropagation();
              onRepeat(deadline);
            }}
            className="w-full mt-2 bg-blue-600 hover:bg-blue-700 text-white text-sm py-1"
          >
            <Repeat className="w-4 h-4 mr-1" />
            Repeat
          </Button>
        )}
      </div>
    </Card>
  );
};

export default DeadlineCard;
