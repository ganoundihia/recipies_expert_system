import React, { useEffect, useState } from 'react'
import './home.css'
import leaf from './pics/Leaf.png'
import blue from './pics/bluebery.png'
import cake from './pics/cakemauve.png'
import macaron from './pics/macaronsmove.png'
import Stepper from '../Stepper/Stepper'

function Home() {
  const [showImage, setShowImage] = useState(false);
  const [showSecondText, setShowSecondText] = useState(false);
  const [showThirdText, setShowThirdText] = useState(false);
  const [showStepper, setShowStepper] = useState(false)

  useEffect(() => {
    // Reveal the subtitle, the blueberry and the call-to-action one after another.
    const timer1 = setTimeout(() => {
      setShowImage(true);
    }, 4000);
    const timer2 = setTimeout(() => {
      setShowSecondText(true);
    }, 2000);
    const timer3 = setTimeout(() => {
      setShowThirdText(true);
    }, 4500);

    return () => {
      clearTimeout(timer1);
      clearTimeout(timer2);
      clearTimeout(timer3);
    };
  }, []);

  return (
    <div className='page'>
        <div className="container">
          <div className="leaf">
            <img src={leaf} alt="" />
          </div>
          <div className="content">
            
            <div className="writing">
              <div className="title">
                <div className="bluebery">
                  <img src={blue} alt="" style={{opacity : showImage ? '1' : '0'}} />
                </div>
                <div className="text">
                  Taste the beauty of our recipes 
                </div>
              </div>
              <div className='subtitle' style={{opacity : showSecondText ? '1' : '0'}}>
                Made with love from our hands to yours
              </div>
              <div className="button" >
                <button style={{opacity : showThirdText ? '1' : '0'}} onClick={() => setShowStepper(true)}>Find your recipe now</button>
              </div>

            </div>
            <div className="images">
              <div className="cake">
                <img src={cake} alt="" />
              </div>
              <div className="macaron">
                <img src = {macaron} alt="" />
              </div>
            </div>
          </div>
        </div>
        <div className="imagebg" />
        <div className="stepper" >
          <Stepper display={showStepper} />
        </div>
    </div>
  )
}

export default Home
