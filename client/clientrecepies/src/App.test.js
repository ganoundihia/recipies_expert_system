import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import App from './App';
import Display, { RECIPES } from './pages/display/Display';
import { STEPS } from './pages/Stepper/Stepper';

test('renders the home page call to action', () => {
  render(<App />);
  expect(screen.getByText(/find your recipe now/i)).toBeInTheDocument();
});

test('every ingredient combination has a recipe in the recipe book', () => {
  const combinations = STEPS.reduce((total, step) => total * step.options.length, 1);
  expect(Object.keys(RECIPES)).toHaveLength(combinations);
  Object.values(RECIPES).forEach(recipe => {
    expect(recipe.ingredients.length).toBeGreaterThan(0);
    expect(recipe.instructions.length).toBeGreaterThan(0);
  });
});

test('displays the inferred recipe with the expert reasoning', () => {
  const state = { recipe: 'Lemon_butter_cookies', trace: ['R-F1: all-purpose flour gives a versatile, everyday crumb'] };
  render(
    <MemoryRouter initialEntries={[{ pathname: '/display', state }]}>
      <Display />
    </MemoryRouter>
  );
  expect(screen.getByText('Lemon butter cookies')).toBeInTheDocument();
  expect(screen.getByText('1 cup butter, softened')).toBeInTheDocument();
  expect(screen.getByText(/why this recipe/i)).toBeInTheDocument();
});

test('displays the server error when no recipe could be inferred', () => {
  const state = { error: 'The recipe server is unreachable. Please try again later.' };
  render(
    <MemoryRouter initialEntries={[{ pathname: '/display', state }]}>
      <Display />
    </MemoryRouter>
  );
  expect(screen.getByText(state.error)).toBeInTheDocument();
  expect(screen.queryByText('Ingredients')).not.toBeInTheDocument();
});
