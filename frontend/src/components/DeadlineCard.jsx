import React from 'react';
import { Clock, X, Edit3, MoreVertical, Repeat, CheckCircle2 } from 'lucide-react';
import { Button } from './ui/button';
import { Tooltip, TooltipContent, TooltipTrigger } from './ui/tooltip';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from './ui/dropdown-menu';
import { Card } from './ui/card';
import { Badge } from './ui/badge';
import { cn } from '../lib/utils';
import { MANUAL_DOT_COLORS } from '../lib/calendar-utils';
import CircularProgress from './CircularProgress';
import PlanningModeInput from './PlanningModeInput';

const truncateText = (text, maxLength = 25) => {
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength) + '...';
};

const DeadlineCard = ({ deadline, timeLeft, progressColor, progressPercentage, isPulsing, onEdit, onDelete, onComplete, onRepeat, isRegularSection, isPlanningMode, onUpdateDaysNeeded, planningSubMode, onSelectForManual, isManualSelected, manualColorIndex, isNew, onMarkSeen }) => {
  const showRepeatButton = deadline.isRecurring && timeLeft.isOverdue;
  const isManualMode = isPlanningMode && planningSubMode === 'manual';

  const handleClick = () => {
    if (isManualMode) {
      onSelectForManual?.(deadline.id);
    } else {
      onEdit(deadline);
    }
  };

  const manualSelectedRingColor = isManualSelected
    ? 'ring-2 ring-offset-2 dark:ring-offset-slate-900 ring-blue-400 dark:ring-blue-500 border-blue-400 dark:border-blue-500'
    : '';

  return (
    <Card
      key={deadline.id}
      className={cn(
        'relative p-6 bg-white dark:bg-slate-800 shadow-md hover:shadow-xl hover:ring-2 hover:ring-slate-300 dark:hover:ring-slate-600 hover:ring-offset-2 dark:hover:ring-offset-slate-900 transition-all duration-200 hover:scale-105 cursor-pointer border',
        isManualMode && isManualSelected ? manualSelectedRingColor
          : isPlanningMode ? 'border-blue-300 dark:border-blue-600 ring-1 ring-blue-200 dark:ring-blue-800'
          : 'border-slate-200 dark:border-slate-700'
      )}
      onClick={handleClick}
    >
      {/* Planning mode input / manual indicator / 3-dot menu */}
      {isManualMode ? (
        manualColorIndex != null && (
          <div className="absolute -top-2 -right-2 z-10">
            <span className={cn('block w-4 h-4 rounded-full ring-2 ring-white dark:ring-slate-800', MANUAL_DOT_COLORS[manualColorIndex] || MANUAL_DOT_COLORS[0])} />
          </div>
        )
      ) : isPlanningMode ? (
        <div className="absolute -top-3 -right-3 z-10">
          <PlanningModeInput deadline={deadline} onUpdate={onUpdateDaysNeeded} />
        </div>
      ) : (
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
      )}

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

      {/* NEW badge — Clash Royale style */}
      {isNew && !isPlanningMode && (
        <div
          className="absolute -top-3 left-1/2 -translate-x-1/2 z-20 animate-new-badge-entrance"
          onClick={(e) => {
            e.stopPropagation();
            onMarkSeen(deadline.id);
          }}
        >
          <span className="new-badge-sparkle relative inline-flex items-center px-3 py-1 text-xs font-black tracking-wider text-white uppercase rounded-full shadow-lg cursor-pointer animate-new-badge-glow bg-gradient-to-r from-yellow-400 via-amber-500 to-yellow-400 border border-yellow-300 hover:scale-110 transition-transform duration-200">
            NEW
          </span>
        </div>
      )}

      <div className="flex flex-col items-center space-y-4 mt-4">
        {/* Circular Progress */}
        <CircularProgress
          percentage={progressPercentage}
          color={progressColor}
          isPulsing={isPulsing}
        >
          <Clock className="w-6 h-6 text-slate-600 dark:text-slate-400 mb-1" />
          <div className="text-center">
            <div className="text-xs font-mono text-slate-700 dark:text-slate-300">
              {timeLeft.isOverdue ? (
                <span className="text-red-600 font-semibold">OVERDUE</span>
              ) : (
                `${timeLeft.days}d ${timeLeft.hours}h`
              )}
            </div>
            <div className="text-xs font-mono text-slate-500 dark:text-slate-400">
              {timeLeft.isOverdue ? '' : `${timeLeft.minutes}m ${timeLeft.seconds}s`}
            </div>
          </div>
        </CircularProgress>

        {/* Name and Task */}
        <div className="text-center">
          <h3 className="font-semibold text-slate-800 dark:text-slate-100 text-lg">{deadline.name}</h3>
          {deadline.task && (
            <Tooltip>
              <TooltipTrigger asChild>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 cursor-help">
                  {truncateText(deadline.task)}
                </p>
              </TooltipTrigger>
              <TooltipContent className="max-w-xs">
                <p>{deadline.task}</p>
              </TooltipContent>
            </Tooltip>
          )}
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
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
