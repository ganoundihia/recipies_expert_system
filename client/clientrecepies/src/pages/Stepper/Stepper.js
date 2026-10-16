import { useState } from 'react'
import axios from 'axios'
import { useNavigate } from 'react-router-dom'
import './stepper.css'
import Circle from '../circles/Circle'
import Option from '../option/Option'
import prev from './pics/prev.png'
import next from './pics/Next.png'

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:7000'

// One step per ingredient category. `id` is the key sent to the expert system,
// each option `value` must match a choice declared in server/expert_system.py.
export const STEPS = [
  {
    id: 'flour',
    name: 'Flour and Semolina',
    options: [
      { value: 'all_purpose_flour', label: 'All-purpose flour' },
      { value: 'cake_flour', label: 'Cake flour' },
      { value: 'semolina', label: 'Semolina' },
      { value: 'bread_flour', label: 'Bread flour' }
    ]
  },
  {
    id: 'fat',
    name: 'Fats and Oils',
    options: [
      { value: 'butter', label: 'Butter' },
      { value: 'margarine', label: 'Margarine' },
      { value: 'vegetable_oil', label: 'Vegetable oil' }
    ]
  },
  {
    id: 'flavor',
    name: 'Flavorings and Extracts',
    options: [
      { value: 'lemon_orange_extract', label: 'Lemon/orange extract' },
      { value: 'coffee_extract', label: 'Coffee extract' },
      { value: 'vanilla', label: 'Vanilla extract' }
    ]
  }
]

const EMPTY_SELECTION = Object.fromEntries(STEPS.map(step => [step.id, '']))

function Stepper({ display }) {
  const [currentIndex, setCurrentIndex] = useState(0)
  const [selection, setSelection] = useState(EMPTY_SELECTION)
  const navigate = useNavigate()

  const currentStep = STEPS[currentIndex]
  const isFirstStep = currentIndex === 0
  const isLastStep = currentIndex === STEPS.length - 1
  const isComplete = STEPS.every(step => selection[step.id] !== '')

  const select = (value) => {
    setSelection(prevSelection => ({ ...prevSelection, [currentStep.id]: value }))
  }

  const goTo = (index) => {
    setCurrentIndex(Math.min(Math.max(index, 0), STEPS.length - 1))
  }

  const handleSend = async () => {
    navigate('/wait')
    try {
      const { data } = await axios.post(`${API_URL}/recommend`, selection)
      navigate('/display', { state: { recipe: data.recipe, trace: data.trace } })
    } catch (error) {
      const message = error.response?.data?.error || 'The recipe server is unreachable. Please try again later.'
      navigate('/display', { state: { error: message } })
    }
  }

  return (
    <div className='steppercontainer'>
      <div className="card" style={{ display: display ? 'flex' : 'none' }}>
        <div className="card2">
          <div className="cercles">
            {STEPS.map((step, index) => (
              <Circle
                key={step.id}
                num={index + 1}
                isFirst={index === 0}
                filled={selection[step.id] !== ''}
                onClick={() => goTo(index)}
              />
            ))}
          </div>
          <div className="cardtitle">
            Choose your {currentStep.name}
          </div>
          <div className="optionscontainer">
            <div className="prev" style={{ opacity: isFirstStep ? '0' : '1' }} onClick={() => goTo(currentIndex - 1)}>
              <img src={prev} alt="Previous step" />
            </div>
            <div className="options">
              {currentStep.options.map(option => (
                <Option
                  key={option.value}
                  label={option.label}
                  selected={selection[currentStep.id] === option.value}
                  onSelect={() => select(option.value)}
                />
              ))}
            </div>
            <div className="next" style={{ opacity: isLastStep ? '0' : '1' }} onClick={() => goTo(currentIndex + 1)}>
              <img src={next} alt="Next step" />
            </div>
          </div>
          <div className="donebutton" style={{ opacity: isLastStep && isComplete ? '1' : '0' }}>
            <button onClick={handleSend} disabled={!(isLastStep && isComplete)}>
              Done
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Stepper
