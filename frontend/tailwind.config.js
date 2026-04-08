/** @type {import('tailwindcss').Config} */
module.exports = {
    darkMode: ["class"],
    content: [
    "./src/**/*.{js,jsx,ts,tsx}",
    "./public/index.html"
  ],
  theme: {
  	extend: {
  		borderRadius: {
  			lg: 'var(--radius)',
  			md: 'calc(var(--radius) - 2px)',
  			sm: 'calc(var(--radius) - 4px)'
  		},
  		colors: {
  			background: 'hsl(var(--background))',
  			foreground: 'hsl(var(--foreground))',
  			card: {
  				DEFAULT: 'hsl(var(--card))',
  				foreground: 'hsl(var(--card-foreground))'
  			},
  			popover: {
  				DEFAULT: 'hsl(var(--popover))',
  				foreground: 'hsl(var(--popover-foreground))'
  			},
  			primary: {
  				DEFAULT: 'hsl(var(--primary))',
  				foreground: 'hsl(var(--primary-foreground))'
  			},
  			secondary: {
  				DEFAULT: 'hsl(var(--secondary))',
  				foreground: 'hsl(var(--secondary-foreground))'
  			},
  			muted: {
  				DEFAULT: 'hsl(var(--muted))',
  				foreground: 'hsl(var(--muted-foreground))'
  			},
  			accent: {
  				DEFAULT: 'hsl(var(--accent))',
  				foreground: 'hsl(var(--accent-foreground))'
  			},
  			destructive: {
  				DEFAULT: 'hsl(var(--destructive))',
  				foreground: 'hsl(var(--destructive-foreground))'
  			},
  			border: 'hsl(var(--border))',
  			input: 'hsl(var(--input))',
  			ring: 'hsl(var(--ring))',
  			chart: {
  				'1': 'hsl(var(--chart-1))',
  				'2': 'hsl(var(--chart-2))',
  				'3': 'hsl(var(--chart-3))',
  				'4': 'hsl(var(--chart-4))',
  				'5': 'hsl(var(--chart-5))'
  			}
  		},
  		keyframes: {
  			'accordion-down': {
  				from: {
  					height: '0'
  				},
  				to: {
  					height: 'var(--radix-accordion-content-height)'
  				}
  			},
  			'accordion-up': {
  				from: {
  					height: 'var(--radix-accordion-content-height)'
  				},
  				to: {
  					height: '0'
  				}
  			},
  			'new-badge-glow': {
  				'0%, 100%': {
  					boxShadow: '0 0 5px rgba(255, 215, 0, 0.5), 0 0 10px rgba(255, 165, 0, 0.3)'
  				},
  				'50%': {
  					boxShadow: '0 0 15px rgba(255, 215, 0, 0.8), 0 0 30px rgba(255, 165, 0, 0.5), 0 0 45px rgba(255, 215, 0, 0.2)'
  				}
  			},
  			'new-badge-entrance': {
  				'0%': {
  					transform: 'translateX(-50%) scale(0) rotate(-15deg)',
  					opacity: '0'
  				},
  				'60%': {
  					transform: 'translateX(-50%) scale(1.3) rotate(3deg)',
  					opacity: '1'
  				},
  				'80%': {
  					transform: 'translateX(-50%) scale(0.95) rotate(-1deg)'
  				},
  				'100%': {
  					transform: 'translateX(-50%) scale(1) rotate(0deg)'
  				}
  			}
  		},
  		animation: {
  			'accordion-down': 'accordion-down 0.2s ease-out',
  			'accordion-up': 'accordion-up 0.2s ease-out',
  			'new-badge-glow': 'new-badge-glow 1.5s ease-in-out infinite',
  			'new-badge-entrance': 'new-badge-entrance 0.6s cubic-bezier(0.34, 1.56, 0.64, 1) forwards'
  		}
  	}
  },
  plugins: [require("tailwindcss-animate")],
};