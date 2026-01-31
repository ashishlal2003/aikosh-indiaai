import { BrowserRouter, Routes, Route } from 'react-router-dom';
import HomePage from './pages/HomePage';
import NewClaimPage from './pages/NewClaimPage';
import ClaimDetailPage from './pages/ClaimDetailPage';
import DashboardPage from './pages/DashboardPage';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/new-claim" element={<NewClaimPage />} />
        <Route path="/claim/:id" element={<ClaimDetailPage />} />
        <Route path="/dashboard" element={<DashboardPage />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
