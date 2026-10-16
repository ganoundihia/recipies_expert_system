import React from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import './display.css'
import leaf from '../Home/pics/Leaf.png'
import blue from '../Home/pics/bluebery.png'
import cake from './pics/cake.png'
import side from './pics/macarronside.png'
import heart from '../waitpage/pics/heart.png'

// Recipe book, keyed by the recipe names the expert system (server/expert_system.py) can infer.
export const RECIPES = {
  // --- All-purpose flour ---------------------------------------------------
  Lemon_butter_cookies: {
    ingredients: ['2 cups all-purpose flour', '1 cup butter, softened', '1/2 cup powdered sugar', '1 teaspoon lemon or orange extract', '1 pinch of salt'],
    instructions: [
      'Preheat your oven to 350°F (175°C) and line a baking sheet with parchment paper.',
      'Cream the softened butter and powdered sugar until light and fluffy.',
      'Mix in the lemon or orange extract, then gradually add the flour and salt until a soft dough forms.',
      'Roll the dough into small balls, place them on the sheet and flatten each one slightly with a fork.',
      'Bake for 12 to 15 minutes, until the edges are lightly golden.',
      'Let the cookies rest on the sheet for 5 minutes, then cool completely on a wire rack.'
    ]
  },
  Vanilla_pound_cake: {
    ingredients: ['2 cups all-purpose flour', '1 cup butter, softened', '1 cup granulated sugar', '4 eggs', '2 teaspoons vanilla extract', '1 teaspoon baking powder', '1/4 cup milk'],
    instructions: [
      'Preheat your oven to 350°F (175°C) and grease a 9x5-inch loaf pan.',
      'Cream the butter and sugar until pale and fluffy, about 4 minutes.',
      'Beat in the eggs one at a time, then the vanilla extract.',
      'Whisk the flour with the baking powder and fold it in, alternating with the milk.',
      'Pour into the pan and bake for 55 to 65 minutes, until a toothpick comes out clean.',
      'Cool in the pan for 10 minutes, then turn out onto a wire rack.'
    ]
  },
  Coffee_cake: {
    ingredients: ['2 cups all-purpose flour', '3/4 cup butter, softened', '1 cup brown sugar', '2 eggs', '1 tablespoon coffee extract', '1 1/2 teaspoons baking powder', '1/2 cup milk', '1 teaspoon cinnamon'],
    instructions: [
      'Preheat your oven to 350°F (175°C) and grease an 8-inch square pan.',
      'Rub 1/2 cup flour, 1/4 cup sugar and 3 tablespoons butter together to make a crumb topping.',
      'Cream the remaining butter and sugar, then beat in the eggs and coffee extract.',
      'Fold in the remaining flour, baking powder and cinnamon, alternating with the milk.',
      'Spread the batter in the pan and scatter the crumb topping over it.',
      'Bake for 35 to 40 minutes, until golden and set in the center.'
    ]
  },
  Lemon_Drizzle_Muffins: {
    ingredients: ['2 cups all-purpose flour', '1/2 cup vegetable oil', '3/4 cup granulated sugar', '2 eggs', '3/4 cup milk', '2 teaspoons lemon or orange extract', '2 teaspoons baking powder', '1/2 cup powdered sugar and 1 tablespoon water for the drizzle'],
    instructions: [
      'Preheat your oven to 375°F (190°C) and line a 12-cup muffin tin.',
      'Whisk the oil, sugar, eggs, milk and lemon or orange extract together.',
      'Stir the flour and baking powder in just until combined; a few lumps are fine.',
      'Divide the batter between the cups and bake for 18 to 20 minutes.',
      'Mix the powdered sugar with the water and drizzle it over the warm muffins.'
    ]
  },
  Simple_vanilla_cake: {
    ingredients: ['2 cups all-purpose flour', '1/2 cup vegetable oil', '1 cup granulated sugar', '2 eggs', '1 cup milk', '2 teaspoons vanilla extract', '2 teaspoons baking powder', '1 pinch of salt'],
    instructions: [
      'Preheat your oven to 350°F (175°C) and grease a 9-inch round pan.',
      'Whisk the eggs and sugar until pale, then whisk in the oil, milk and vanilla extract.',
      'Fold in the flour, baking powder and salt until smooth.',
      'Pour into the pan and bake for 30 to 35 minutes, until a toothpick comes out clean.',
      'Cool for 10 minutes in the pan, then on a wire rack.'
    ]
  },
  Coffee_Flavored_Cupcakes: {
    ingredients: ['1 1/2 cups all-purpose flour', '1/2 cup vegetable oil', '3/4 cup granulated sugar', '2 eggs', '1/2 cup milk', '1 tablespoon coffee extract', '1 1/2 teaspoons baking powder'],
    instructions: [
      'Preheat your oven to 350°F (175°C) and line a 12-cup muffin tin.',
      'Whisk the oil, sugar, eggs, milk and coffee extract together.',
      'Stir in the flour and baking powder until just smooth.',
      'Fill the cups two-thirds full and bake for 18 to 22 minutes.',
      'Cool completely before frosting, for example with a coffee buttercream.'
    ]
  },
  Citrus_Shortbread_Cookies: {
    ingredients: ['2 cups all-purpose flour', '1 cup margarine, softened', '1/2 cup powdered sugar', '1 teaspoon lemon or orange extract', '1 pinch of salt'],
    instructions: [
      'Preheat your oven to 325°F (165°C).',
      'Beat the margarine and powdered sugar until smooth, then add the lemon or orange extract.',
      'Mix in the flour and salt until the dough just comes together.',
      'Roll out to 1/4 inch thick, cut into shapes and place on a lined baking sheet.',
      'Chill for 15 minutes, then bake for 15 to 18 minutes, until the edges just start to color.'
    ]
  },
  Margarine_Frosting: {
    ingredients: ['3 tablespoons all-purpose flour', '1 cup milk', '1 cup margarine, softened', '1 cup granulated sugar', '1 teaspoon vanilla extract'],
    instructions: [
      'Whisk the flour into the milk in a saucepan and cook over medium heat, stirring, until thick like pudding.',
      'Transfer to a bowl, cover the surface with plastic wrap and let it cool completely.',
      'Beat the margarine and sugar until very light and the sugar is mostly dissolved, about 5 minutes.',
      'Add the cooled flour paste one spoonful at a time, beating well after each addition.',
      'Beat in the vanilla extract; the frosting should be silky and pipeable. Use it on cakes or cupcakes.'
    ]
  },
  Coffee_Shortbread: {
    ingredients: ['2 cups all-purpose flour', '1 cup margarine, softened', '1/2 cup brown sugar', '1 tablespoon coffee extract', '1 pinch of salt'],
    instructions: [
      'Preheat your oven to 325°F (165°C).',
      'Cream the margarine and brown sugar, then beat in the coffee extract.',
      'Mix in the flour and salt to form a firm dough.',
      'Press into an 8-inch square pan, prick all over with a fork and score into fingers.',
      'Bake for 30 to 35 minutes, then cut along the scores while still warm.'
    ]
  },

  // --- Cake flour ----------------------------------------------------------
  Citrus_Madeleines: {
    ingredients: ['1 cup cake flour', '1/2 cup butter, melted and cooled', '2/3 cup granulated sugar', '3 eggs', '1 teaspoon lemon or orange extract', '1/2 teaspoon baking powder'],
    instructions: [
      'Whisk the eggs and sugar until thick and pale, about 5 minutes.',
      'Add the lemon or orange extract, then gently fold in the flour and baking powder.',
      'Fold in the melted butter, cover and chill the batter for at least 1 hour.',
      'Preheat your oven to 375°F (190°C) and butter and flour a madeleine pan.',
      'Fill each shell three-quarters full and bake for 9 to 11 minutes, until the humps rise and the edges are golden.'
    ]
  },
  Vanilla_Cupcakes_butter: {
    ingredients: ['1 1/2 cups cake flour', '1/2 cup butter, softened', '3/4 cup granulated sugar', '2 eggs', '1/2 cup milk', '2 teaspoons vanilla extract', '1 1/2 teaspoons baking powder'],
    instructions: [
      'Preheat your oven to 350°F (175°C) and line a 12-cup muffin tin.',
      'Cream the butter and sugar until fluffy, then beat in the eggs and vanilla extract.',
      'Fold in the flour and baking powder, alternating with the milk.',
      'Fill the cups two-thirds full and bake for 18 to 20 minutes.',
      'Cool completely before frosting.'
    ]
  },
  Coffee_Cake: {
    ingredients: ['2 cups cake flour', '3/4 cup butter, softened', '1 cup granulated sugar', '3 eggs', '2/3 cup milk', '1 tablespoon coffee extract', '2 teaspoons baking powder'],
    instructions: [
      'Preheat your oven to 350°F (175°C) and grease two 8-inch round pans.',
      'Cream the butter and sugar, then beat in the eggs one at a time and the coffee extract.',
      'Fold in the flour and baking powder, alternating with the milk.',
      'Divide between the pans and bake for 25 to 30 minutes.',
      'Cool, then sandwich and cover the layers with coffee buttercream.'
    ]
  },
  Citrus_Olive_Oil_Cake: {
    ingredients: ['1 3/4 cups cake flour', '2/3 cup vegetable or olive oil', '1 cup granulated sugar', '3 eggs', '3/4 cup milk', '2 teaspoons lemon or orange extract', '2 teaspoons baking powder'],
    instructions: [
      'Preheat your oven to 350°F (175°C) and grease a 9-inch round pan.',
      'Whisk the eggs and sugar until pale, then stream in the oil while whisking.',
      'Whisk in the milk and lemon or orange extract.',
      'Fold in the flour and baking powder until smooth.',
      'Bake for 40 to 45 minutes and dust with powdered sugar once cool.'
    ]
  },
  Vanilla_Cupcakes_oil: {
    ingredients: ['1 1/2 cups cake flour', '1/2 cup vegetable oil', '3/4 cup granulated sugar', '2 eggs', '2/3 cup milk', '2 teaspoons vanilla extract', '1 1/2 teaspoons baking powder'],
    instructions: [
      'Preheat your oven to 350°F (175°C) and line a 12-cup muffin tin.',
      'Whisk the oil, sugar, eggs, milk and vanilla extract together.',
      'Whisk in the flour and baking powder until smooth.',
      'Fill the cups two-thirds full and bake for 17 to 20 minutes.',
      'These stay moist for days; frost once completely cool.'
    ]
  },
  Coffee_Cupcakes: {
    ingredients: ['1 1/2 cups cake flour', '1/2 cup vegetable oil', '3/4 cup brown sugar', '2 eggs', '2/3 cup milk', '1 tablespoon coffee extract', '1 1/2 teaspoons baking powder'],
    instructions: [
      'Preheat your oven to 350°F (175°C) and line a 12-cup muffin tin.',
      'Whisk the oil, brown sugar, eggs, milk and coffee extract together.',
      'Whisk in the flour and baking powder until smooth.',
      'Fill the cups two-thirds full and bake for 18 to 20 minutes.',
      'Top with a mocha or vanilla frosting once cool.'
    ]
  },
  Citrus_Pound_Cake: {
    ingredients: ['2 cups cake flour', '1 cup margarine, softened', '1 cup granulated sugar', '4 eggs', '2 teaspoons lemon or orange extract', '1 teaspoon baking powder', '1/4 cup milk'],
    instructions: [
      'Preheat your oven to 325°F (165°C) and grease a 9x5-inch loaf pan.',
      'Cream the margarine and sugar until light, about 4 minutes.',
      'Beat in the eggs one at a time, then the lemon or orange extract.',
      'Fold in the flour and baking powder, alternating with the milk.',
      'Bake for 60 to 70 minutes, until a toothpick comes out clean, then cool on a rack.'
    ]
  },
  Vanilla_Pound_Cake: {
    ingredients: ['2 cups cake flour', '1 cup margarine, softened', '1 cup granulated sugar', '4 eggs', '2 teaspoons vanilla extract', '1 teaspoon baking powder', '1/4 cup milk'],
    instructions: [
      'Preheat your oven to 325°F (165°C) and grease a 9x5-inch loaf pan.',
      'Cream the margarine and sugar until light, about 4 minutes.',
      'Beat in the eggs one at a time, then the vanilla extract.',
      'Fold in the flour and baking powder, alternating with the milk.',
      'Bake for 60 to 70 minutes, until a toothpick comes out clean, then cool on a rack.'
    ]
  },
  Coffee_Pound_Cake: {
    ingredients: ['2 cups cake flour', '1 cup margarine, softened', '1 cup brown sugar', '4 eggs', '1 tablespoon coffee extract', '1 teaspoon baking powder', '1/4 cup milk'],
    instructions: [
      'Preheat your oven to 325°F (165°C) and grease a 9x5-inch loaf pan.',
      'Cream the margarine and brown sugar until light, about 4 minutes.',
      'Beat in the eggs one at a time, then the coffee extract.',
      'Fold in the flour and baking powder, alternating with the milk.',
      'Bake for 60 to 70 minutes, until a toothpick comes out clean, then cool on a rack.'
    ]
  },

  // --- Semolina ------------------------------------------------------------
  Semolina_Cookies: {
    ingredients: ['1 1/2 cups fine semolina', '1/2 cup all-purpose flour', '3/4 cup butter, softened', '1/2 cup powdered sugar', '1 teaspoon lemon or orange extract', '1/2 teaspoon baking powder'],
    instructions: [
      'Cream the butter and powdered sugar, then add the lemon or orange extract.',
      'Mix in the semolina, flour and baking powder and let the dough rest for 30 minutes.',
      'Preheat your oven to 350°F (175°C) and line a baking sheet.',
      'Shape into walnut-sized balls and flatten them slightly.',
      'Bake for 15 to 18 minutes, until pale golden underneath.'
    ]
  },
  Semolina_Cake: {
    ingredients: ['1 1/2 cups fine semolina', '1/2 cup butter, melted', '3/4 cup granulated sugar', '2 eggs', '1 cup plain yogurt or milk', '2 teaspoons vanilla extract', '2 teaspoons baking powder', 'Syrup: 1 cup sugar, 3/4 cup water'],
    instructions: [
      'Preheat your oven to 350°F (175°C) and grease an 8-inch square pan.',
      'Whisk the eggs and sugar, then add the yogurt, melted butter and vanilla extract.',
      'Stir in the semolina and baking powder and let the batter rest for 15 minutes.',
      'Bake for 30 to 35 minutes, until golden.',
      'Meanwhile simmer the sugar and water for 5 minutes, then pour the warm syrup over the hot cake and let it soak in.'
    ]
  },
  Semolina_Biscotti: {
    ingredients: ['1 cup fine semolina', '1 cup all-purpose flour', '1/4 cup butter, melted', '3/4 cup granulated sugar', '2 eggs', '1 tablespoon coffee extract', '1 teaspoon baking powder', '1/2 cup almonds (optional)'],
    instructions: [
      'Preheat your oven to 350°F (175°C) and line a baking sheet.',
      'Whisk the eggs, sugar, melted butter and coffee extract together.',
      'Stir in the semolina, flour, baking powder and almonds to make a sticky dough.',
      'Shape into two logs and bake for 25 minutes; cool for 10 minutes.',
      'Slice diagonally 1/2 inch thick and bake the slices for 10 minutes per side, until dry and crisp.'
    ]
  },
  Semolina_Citrus_Cake: {
    ingredients: ['1 1/2 cups fine semolina', '1/2 cup all-purpose flour', '1/2 cup vegetable oil', '3/4 cup granulated sugar', '3 eggs', '3/4 cup milk', '2 teaspoons lemon or orange extract', '2 teaspoons baking powder'],
    instructions: [
      'Preheat your oven to 350°F (175°C) and grease a 9-inch round pan.',
      'Whisk the eggs and sugar, then whisk in the oil, milk and lemon or orange extract.',
      'Stir in the semolina, flour and baking powder and let the batter rest for 10 minutes.',
      'Bake for 35 to 40 minutes, until golden and springy.',
      'Brush with a little citrus syrup or dust with powdered sugar.'
    ]
  },
  Semolina_Vanilla_Cake: {
    ingredients: ['1 1/2 cups fine semolina', '1/2 cup all-purpose flour', '1/2 cup vegetable oil', '3/4 cup granulated sugar', '3 eggs', '1 cup milk', '2 teaspoons vanilla extract', '2 teaspoons baking powder'],
    instructions: [
      'Preheat your oven to 350°F (175°C) and grease a 9-inch round pan.',
      'Whisk the eggs and sugar, then whisk in the oil, milk and vanilla extract.',
      'Stir in the semolina, flour and baking powder and let the batter rest for 10 minutes.',
      'Bake for 35 to 40 minutes, until a toothpick comes out clean.',
      'Cool in the pan for 10 minutes before unmolding.'
    ]
  },
  Semolina_Coffee_Cake: {
    ingredients: ['1 1/2 cups fine semolina', '1/2 cup all-purpose flour', '1/2 cup vegetable oil', '3/4 cup brown sugar', '3 eggs', '1 cup milk', '1 tablespoon coffee extract', '2 teaspoons baking powder'],
    instructions: [
      'Preheat your oven to 350°F (175°C) and grease a 9-inch round pan.',
      'Whisk the eggs and brown sugar, then whisk in the oil, milk and coffee extract.',
      'Stir in the semolina, flour and baking powder and let the batter rest for 10 minutes.',
      'Bake for 35 to 40 minutes, until a toothpick comes out clean.',
      'Serve with a coffee glaze or whipped cream.'
    ]
  },
  Semolina_Lemon_Pound_Cake: {
    ingredients: ['1 cup fine semolina', '1 cup all-purpose flour', '1 cup margarine, softened', '1 cup granulated sugar', '4 eggs', '2 teaspoons lemon or orange extract', '1 1/2 teaspoons baking powder'],
    instructions: [
      'Preheat your oven to 325°F (165°C) and grease a 9x5-inch loaf pan.',
      'Cream the margarine and sugar until light, then beat in the eggs one at a time.',
      'Add the lemon or orange extract.',
      'Fold in the semolina, flour and baking powder.',
      'Bake for 55 to 65 minutes, until a toothpick comes out clean.'
    ]
  },
  Semolina_Vanilla_Pound_Cake: {
    ingredients: ['1 cup fine semolina', '1 cup all-purpose flour', '1 cup margarine, softened', '1 cup granulated sugar', '4 eggs', '2 teaspoons vanilla extract', '1 1/2 teaspoons baking powder'],
    instructions: [
      'Preheat your oven to 325°F (165°C) and grease a 9x5-inch loaf pan.',
      'Cream the margarine and sugar until light, then beat in the eggs one at a time.',
      'Add the vanilla extract.',
      'Fold in the semolina, flour and baking powder.',
      'Bake for 55 to 65 minutes, until a toothpick comes out clean.'
    ]
  },
  Semolina_Coffee_Pound_Cake: {
    ingredients: ['1 cup fine semolina', '1 cup all-purpose flour', '1 cup margarine, softened', '1 cup brown sugar', '4 eggs', '1 tablespoon coffee extract', '1 1/2 teaspoons baking powder'],
    instructions: [
      'Preheat your oven to 325°F (165°C) and grease a 9x5-inch loaf pan.',
      'Cream the margarine and brown sugar until light, then beat in the eggs one at a time.',
      'Add the coffee extract.',
      'Fold in the semolina, flour and baking powder.',
      'Bake for 55 to 65 minutes, until a toothpick comes out clean.'
    ]
  },

  // --- Bread flour (enriched sweet breads) ---------------------------------
  Lemon_Bread: {
    ingredients: ['3 1/2 cups bread flour', '1/3 cup butter, softened', '1/3 cup granulated sugar', '1 cup warm milk', '1 egg', '2 1/4 teaspoons instant yeast', '1 teaspoon lemon or orange extract', '1 teaspoon salt'],
    instructions: [
      'Mix the flour, sugar, yeast and salt, then add the warm milk, egg and lemon or orange extract.',
      'Knead for 8 minutes, then knead in the butter until the dough is smooth and elastic.',
      'Cover and let rise for 1 to 1 1/2 hours, until doubled.',
      'Shape into a loaf, place in a greased 9x5-inch pan and let rise for 45 minutes.',
      'Bake at 350°F (175°C) for 30 to 35 minutes, until golden and hollow-sounding when tapped.'
    ]
  },
  Vanilla_Bread: {
    ingredients: ['3 1/2 cups bread flour', '1/3 cup butter, softened', '1/3 cup granulated sugar', '1 cup warm milk', '1 egg', '2 1/4 teaspoons instant yeast', '2 teaspoons vanilla extract', '1 teaspoon salt'],
    instructions: [
      'Mix the flour, sugar, yeast and salt, then add the warm milk, egg and vanilla extract.',
      'Knead for 8 minutes, then knead in the butter until the dough is smooth and elastic.',
      'Cover and let rise for 1 to 1 1/2 hours, until doubled.',
      'Shape into a loaf, place in a greased 9x5-inch pan and let rise for 45 minutes.',
      'Bake at 350°F (175°C) for 30 to 35 minutes, until golden and hollow-sounding when tapped.'
    ]
  },
  Coffee_Bread: {
    ingredients: ['3 1/2 cups bread flour', '1/3 cup butter, softened', '1/3 cup brown sugar', '1 cup warm milk', '1 egg', '2 1/4 teaspoons instant yeast', '1 tablespoon coffee extract', '1 teaspoon salt'],
    instructions: [
      'Mix the flour, sugar, yeast and salt, then add the warm milk, egg and coffee extract.',
      'Knead for 8 minutes, then knead in the butter until the dough is smooth and elastic.',
      'Cover and let rise for 1 to 1 1/2 hours, until doubled.',
      'Shape into a loaf, place in a greased 9x5-inch pan and let rise for 45 minutes.',
      'Bake at 350°F (175°C) for 30 to 35 minutes, until browned and hollow-sounding when tapped.'
    ]
  },
  Citrus_Bread: {
    ingredients: ['3 1/2 cups bread flour', '1/4 cup vegetable oil', '1/3 cup granulated sugar', '1 cup warm water', '1 egg', '2 1/4 teaspoons instant yeast', '1 teaspoon lemon or orange extract', '1 teaspoon salt'],
    instructions: [
      'Mix the flour, sugar, yeast and salt, then add the warm water, oil, egg and lemon or orange extract.',
      'Knead for 10 minutes until smooth and elastic.',
      'Cover and let rise for about 1 hour, until doubled.',
      'Shape into a braid or loaf, place on a lined sheet or in a pan and let rise for 40 minutes.',
      'Bake at 350°F (175°C) for 25 to 30 minutes, until golden.'
    ]
  },
  Vanilla_Bread_oil: {
    ingredients: ['3 1/2 cups bread flour', '1/4 cup vegetable oil', '1/3 cup granulated sugar', '1 cup warm milk', '1 egg', '2 1/4 teaspoons instant yeast', '2 teaspoons vanilla extract', '1 teaspoon salt'],
    instructions: [
      'Mix the flour, sugar, yeast and salt, then add the warm milk, oil, egg and vanilla extract.',
      'Knead for 10 minutes until smooth and elastic.',
      'Cover and let rise for about 1 hour, until doubled.',
      'Shape into a loaf, place in a greased 9x5-inch pan and let rise for 40 minutes.',
      'Bake at 350°F (175°C) for 30 to 35 minutes, until golden.'
    ]
  },
  Coffee_Bread_oil: {
    ingredients: ['3 1/2 cups bread flour', '1/4 cup vegetable oil', '1/3 cup brown sugar', '1 cup warm milk', '1 egg', '2 1/4 teaspoons instant yeast', '1 tablespoon coffee extract', '1 teaspoon salt'],
    instructions: [
      'Mix the flour, sugar, yeast and salt, then add the warm milk, oil, egg and coffee extract.',
      'Knead for 10 minutes until smooth and elastic.',
      'Cover and let rise for about 1 hour, until doubled.',
      'Shape into a loaf, place in a greased 9x5-inch pan and let rise for 40 minutes.',
      'Bake at 350°F (175°C) for 30 to 35 minutes, until well browned.'
    ]
  },
  Lemon_Bread_margarine: {
    ingredients: ['3 1/2 cups bread flour', '1/3 cup margarine, softened', '1/3 cup granulated sugar', '1 cup warm milk', '1 egg', '2 1/4 teaspoons instant yeast', '1 teaspoon lemon or orange extract', '1 teaspoon salt'],
    instructions: [
      'Mix the flour, sugar, yeast and salt, then add the warm milk, egg and lemon or orange extract.',
      'Knead for 8 minutes, then knead in the margarine until the dough is smooth.',
      'Cover and let rise for 1 to 1 1/2 hours, until doubled.',
      'Divide into 12 pieces, roll into buns and let rise on a lined sheet for 40 minutes.',
      'Bake at 375°F (190°C) for 15 to 18 minutes, until golden.'
    ]
  },
  Vanilla_Bread_margarine: {
    ingredients: ['3 1/2 cups bread flour', '1/3 cup margarine, softened', '1/3 cup granulated sugar', '1 cup warm milk', '1 egg', '2 1/4 teaspoons instant yeast', '2 teaspoons vanilla extract', '1 teaspoon salt'],
    instructions: [
      'Mix the flour, sugar, yeast and salt, then add the warm milk, egg and vanilla extract.',
      'Knead for 8 minutes, then knead in the margarine until the dough is smooth.',
      'Cover and let rise for 1 to 1 1/2 hours, until doubled.',
      'Divide into 12 pieces, roll into buns and let rise on a lined sheet for 40 minutes.',
      'Bake at 375°F (190°C) for 15 to 18 minutes, until golden.'
    ]
  },
  Coffee_Bread_margarine: {
    ingredients: ['3 1/2 cups bread flour', '1/3 cup margarine, softened', '1/3 cup brown sugar', '1 cup warm milk', '1 egg', '2 1/4 teaspoons instant yeast', '1 tablespoon coffee extract', '1 teaspoon salt'],
    instructions: [
      'Mix the flour, sugar, yeast and salt, then add the warm milk, egg and coffee extract.',
      'Knead for 8 minutes, then knead in the margarine until the dough is smooth.',
      'Cover and let rise for 1 to 1 1/2 hours, until doubled.',
      'Divide into 12 pieces, roll into buns and let rise on a lined sheet for 40 minutes.',
      'Bake at 375°F (190°C) for 15 to 18 minutes, until browned.'
    ]
  }
}

const formatTitle = (recipeName) => recipeName.replace(/_/g, ' ')

function Display() {
  const location = useLocation()
  const navigate = useNavigate()
  const { recipe: recipeName, trace = [], error } = location.state || {}
  const recipe = RECIPES[recipeName]

  const title = recipe
    ? formatTitle(recipeName)
    : error || 'No recipe selected yet'

  return (
    <div className='displaycontainer'>
      <div className="intro">
        <div className="container">
          <div className="leaf">
            <img src={leaf} alt="" />
          </div>
          <div className="content">
            <div className="writing">
              <div className="title">
                <div className="bluebery">
                  <img src={blue} alt="" />
                </div>
                <div className="text">
                  {title}
                </div>
              </div>
            </div>
            <div className="images">
              <div className="macaron">
                <img src={cake} alt="" />
              </div>
            </div>
          </div>
        </div>
        <div className="imagebg" />
      </div>
      {recipe && (
        <>
          <div className="ingredientcontainer">
            <div className="sideimage">
              <img src={side} alt="" />
            </div>
            <div className="ingredient">
              <div className="ingredienttitle">
                Ingredients
              </div>
              <div className="list">
                <ul>
                  {recipe.ingredients.map(item => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
          <div className="instructionscontainer">
            <div className="instructionstitle">
              Instructions
            </div>
            <div className="list">
              <ol>
                {recipe.instructions.map(item => (
                  <li key={item}>{item}</li>
                ))}
              </ol>
            </div>
          </div>
          {trace.length > 0 && (
            <details className="instructionscontainer reasoning">
              <summary className="instructionstitle">Why this recipe?</summary>
              <ul className="list">
                {trace.map(step => (
                  <li key={step}>{step}</li>
                ))}
              </ul>
            </details>
          )}
        </>
      )}
      <div className="button">
        <button onClick={() => navigate('/')}>Back to home page</button>
      </div>
      <footer>
        Made With Love and Sweet <img src={heart} alt="" />
      </footer>
    </div>
  )
}

export default Display
