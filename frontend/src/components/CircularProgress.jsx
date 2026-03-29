import React from 'react';

const CircularProgress = ({ percentage, color, isPulsing, children }) => {
  const radius = 45;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (percentage / 100) * circumference;

  return (
    <div className="relative w-32 h-32">
      <svg className="w-full h-full transform -rotate-90" viewBox="0 0 100 100">
        <circle cx="50" cy="50" r={radius} stroke="currentColor" strokeWidth="2" fill="transparent" className="text-slate-200 dark:text-slate-700" />
        <circle cx="50" cy="50" r={radius} stroke="currentColor" strokeWidth="3" fill="transparent"
          strokeDasharray={circumference} strokeDashoffset={strokeDashoffset} strokeLinecap="round"
          className={`${color} transition-all duration-300 ${isPulsing ? 'animate-pulse' : ''}`}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        {children}
      </div>
    </div>
  );
};

export default CircularProgress;
