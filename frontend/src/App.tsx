import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Layout } from './components/Layout';
import { Home } from './components/Home';
import { Chat } from './components/Chat';
import { AdminPanel } from './components/AdminPanel';
import { MarkdownTest } from './components/MarkdownTest';

function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/chat" element={<Chat />} />
          <Route path="/admin" element={<AdminPanel />} />
          <Route path="/markdown-test" element={<MarkdownTest />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Layout>
    </Router>
  );
}

export default App;
