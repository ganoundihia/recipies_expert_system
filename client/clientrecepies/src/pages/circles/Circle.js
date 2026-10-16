import React from 'react'
import './circles.css'

function Circle({ num, isFirst, filled, onClick }) {
  return (
    <div className='circlecontainer'>
      <div className="line" style={{ display: isFirst ? 'none' : 'flex' }} />
      <div
        className="num"
        style={{
          backgroundColor: filled ? '#964262' : 'white',
          color: filled ? 'white' : '#964262',
          border: filled ? '0' : '1px solid black'
        }}
        onClick={onClick}
      >
        {num}
      </div>
    </div>
  )
}

export default Circle
