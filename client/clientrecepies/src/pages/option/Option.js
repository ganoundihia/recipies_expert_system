import React from 'react'
import './option.css'

const SELECTED_STYLE = {
  color: 'white',
  backgroundColor: '#964262'
}

function Option({ label, selected, onSelect }) {
  return (
    <div className='op' onClick={onSelect} style={selected ? SELECTED_STYLE : undefined}>
      {label}
    </div>
  )
}

export default Option
