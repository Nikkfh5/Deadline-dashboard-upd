# Deadline Dashboard

A modern, responsive deadline tracking application built with React and FastAPI.

## Features

✨ **Core Functionality**
- Create and manage deadlines with real-time countdown timers
- Circular progress indicators showing time remaining
- Support for both regular and recurring (temporary) deadlines
- Edit and delete deadlines with intuitive UI

🎯 **Key Improvements (v2.0)**
- **English Interface**: Fully translated from Russian to English
- **Smart Layout**: Common deadlines displayed first, temporary deadlines in collapsible section below
- **Collapsible Sections**: Temporary deadlines can be expanded/collapsed to reduce visual clutter
- **Custom Periodicity**: Fixed bug allowing custom recurring periods (e.g., every 5 days)

🔧 **Technical Features**
- Real-time updates with live countdown timers
- Responsive design with Tailwind CSS
- Modern UI components using Radix UI
- Local storage persistence
- Madrid timezone support
- REST API backend with MongoDB

## Tech Stack

**Frontend:**
- React 19
- Tailwind CSS
- Radix UI Components
- Axios for API calls
- React Router Dom

**Backend:**
- FastAPI (Python)
- MongoDB with Motor (async driver)
- Pydantic for data validation
- CORS support

## Getting Started

### Prerequisites
- Node.js (v16+)
- Python (v3.9+)
- MongoDB
- Yarn package manager

### Installation

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd deadline-dashboard
   ```

2. **Install frontend dependencies**
   ```bash
   cd frontend
   yarn install
   ```

3. **Install backend dependencies**
   ```bash
   cd ../backend
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   
   Create `backend/.env`:
   ```
   MONGO_URL=mongodb://localhost:27017
   DB_NAME=deadline_tracker
   CORS_ORIGINS=http://localhost:3000
   ```
   
   Create `frontend/.env`:
   ```
   REACT_APP_BACKEND_URL=http://localhost:8001
   ```

### Running the Application

1. **Start MongoDB** (if not already running)
   ```bash
   mongod
   ```

2. **Start the backend server**
   ```bash
   cd backend
   uvicorn server:app --host 0.0.0.0 --port 8001 --reload
   ```

3. **Start the frontend development server**
   ```bash
   cd frontend
   yarn start
   ```

4. **Open your browser**
   Navigate to `http://localhost:3000`

## Usage

### Creating Deadlines

1. Click "Add Deadline" button
2. Fill in the form:
   - **Name**: Person or project name
   - **Task**: Description of what needs to be done
   - **Due Date**: When the deadline expires
   - **Make temporary**: Check for recurring deadlines
   - **Period**: Select or enter custom recurring period

### Managing Deadlines

- **Edit**: Click on any deadline card to edit
- **Delete**: Use the 3-dot menu on each card
- **Repeat**: For overdue recurring deadlines, use the Repeat button
- **Collapse/Expand**: Click on "Temporary" section header to show/hide

### Deadline Types

**Common Deadlines**: Regular one-time deadlines displayed prominently at the top

**Temporary Deadlines**: Recurring deadlines that reset automatically, displayed in collapsible section below

## Project Structure

```
deadline-dashboard/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ui/           # Reusable UI components
│   │   │   └── DeadlineTracker.jsx  # Main component
│   │   ├── App.js
│   │   ├── mock.js           # Sample data
│   │   └── ...
│   ├── public/
│   ├── package.json
│   └── ...
├── backend/
│   ├── server.py             # FastAPI application
│   ├── requirements.txt
│   └── .env.example
├── tests/
└── README.md
```

## Recent Updates

### v2.0 - English Translation & UX Improvements
- 🌍 Complete English translation of interface
- 📋 Reordered sections: Common deadlines first, Temporary second
- 🔽 Made Temporary section collapsible to reduce clutter
- 🐛 Fixed custom periodicity input bug
- ✨ Improved form validation and user experience

## API Endpoints

- `GET /api/` - Health check
- `GET /api/status` - Get all status checks
- `POST /api/status` - Create new status check
- (Additional deadline-specific endpoints can be added)

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

If you encounter any issues or have questions, please open an issue on GitHub.
