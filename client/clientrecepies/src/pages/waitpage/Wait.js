import React from 'react'
import './wait.css'
import heart from './pics/heart.png'
import batteur from "./pics/batteur.png";


function Wait() {


  return (
    <div className='waitcontainer'>
        <div className="images">
            <div className="heart">
                <img src={heart} className='one' alt="" />
                <img src={heart} className='two' alt="" />
                <img src={heart} className='three' alt="" />
            </div>
            <div className="batteur">
                <img src={batteur} alt="" />
            </div>   
        </div>
        <div className="writes">
            <div className="first">
                Please wait for a moment
            </div>
            <div className="second">
                ...
            </div>
        </div>

    </div>
  )
}

export default Wait
