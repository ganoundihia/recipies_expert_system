import './App.css';
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';
import Home from './pages/Home/Home';
import Wait from './pages/waitpage/Wait';
import Display from './pages/display/Display';

function App() {
  return (
    <div className="App">
      <Router>
        <Routes>
          <Route path='/' element={<Home />} />
          <Route path='/wait' element={<Wait />} />
          <Route path='/display' element={<Display />} />
        </Routes>
      </Router>
    </div>
  );
}

export default App;
