import { useState } from 'react'
import Sidebar from './components/Sidebar'
import Dashboard from './components/Dashboard'
import Search from './components/Search'
import RAGChat from './components/RAGChat'
import Ingest from './components/Ingest'
import VideoList from './components/VideoList'

export default function App() {
  const [page, setPage] = useState('dashboard')

  return (
    <>
      <Sidebar active={page} onNavigate={setPage} />
      <main className="main-content">
        {page === 'dashboard' && <Dashboard />}
        {page === 'search' && <Search onNavigate={setPage} />}
        {page === 'rag' && <RAGChat />}
        {page === 'ingest' && <Ingest />}
        {page === 'videos' && <VideoList />}
      </main>
    </>
  )
}
