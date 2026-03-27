import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Accounts from './pages/Accounts'
import AccountDetail from './pages/AccountDetail'
import Sequences from './pages/Sequences'
import SequenceDetail from './pages/SequenceDetail'
import Messages from './pages/Messages'
import Decks from './pages/Decks'
import CRM from './pages/CRM'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/accounts" element={<Accounts />} />
        <Route path="/accounts/:id" element={<AccountDetail />} />
        <Route path="/sequences" element={<Sequences />} />
        <Route path="/sequences/:id" element={<SequenceDetail />} />
        <Route path="/messages" element={<Messages />} />
        <Route path="/decks" element={<Decks />} />
        <Route path="/crm" element={<CRM />} />
      </Route>
    </Routes>
  )
}
