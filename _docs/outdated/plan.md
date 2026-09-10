# Coffee Project MVP — Eje Cafetero Visual Journey

## Current build phase

This MVP is being built **backend-first**. The initial deliverable is a data pipeline (ETL) and an API that model coffees from the Eje Cafetero and, critically, the causal relationships between origin, environment, variety, processing, roasting, brewing, and flavor — not just flat facts about each coffee.

The visual/interactive web experience described throughout this document remains the product vision, but it is deferred to a later phase, where it will be built as a separate frontend that consumes this API.

## Product concept

An immersive visual experience where people explore coffees from Colombia's Eje Cafetero and discover the chain of factors that make each coffee taste different.

## Target user

Home coffee enthusiasts who want to understand coffee more deeply.

## Geographic scope

Colombia's Eje Cafetero.

## Core question

**Why does this coffee taste different?**

The experience should help users understand the relationship between coffee production, environment, processing, roasting, brewing, and flavor.

## Core experience

The user enters through a beautiful visual **collection of coffees from the Eje Cafetero** and selects one coffee to explore.

The selected coffee becomes the center of an interconnected visual story rather than a collection of separate information pages.

## Visual journey

The default learning path is:

**Coffee → Origin → Environment → Variety → Processing → Roasting → Brewing → Flavor**

The experience should show how these elements relate to one another and, where appropriate, explain cause-and-effect relationships.

Example:

> High altitude  
> ↓  
> slower cherry development  
> ↓  
> changes in coffee characteristics  
> ↓  
> processing choices  
> ↓  
> roasting  
> ↓  
> flavors perceived in the cup

## Navigation model

Use a **guided journey + free exploration** model.

- The app guides the user through a recommended visual story.
- Users can click or tap individual elements to investigate them.
- Users can ask “Why?” by opening deeper contextual explanations.
- The experience should remain understandable even when users explore out of order.

## Visual direction

The product should feel more like an **interactive museum or digital story** than a traditional coffee website or database.

Prioritize:

- Large, engaging imagery
- Illustrations and diagrams
- Motion and transitions
- Visual relationships and connections
- Short contextual explanations
- Minimal blocks of text
- A strong sense of place and landscape

The visual layer is not decoration; it is the primary mechanism for learning.

Technical approach and tech stack are documented separately in [`architecture.md`](./architecture.md).

## MVP scope

### Phase 1 (current focus): Data + API

- A curated dataset of coffees from the Eje Cafetero
- Structured data for origin and regional context, environment and altitude, variety, processing, roasting, brewing, and flavor/sensory characteristics
- An ETL pipeline that ingests and validates curated source data into a normalized database
- An API exposing coffees and the causal relationships between factors (e.g., altitude → cherry development → processing choices → flavor)

### Phase 2 (later): Visual web experience

- A visual coffee detail / journey experience, built as a frontend consuming the Phase 1 API
- Guided storytelling with interactive exploration
- Visual connections between factors, illustrations, motion and transitions
- Guided journey + free exploration navigation model

(See "Visual journey," "Navigation model," and "Visual direction" above — these describe the product vision for this later phase.)

### Explicitly exclude from MVP

- Marketplace or coffee sales
- Social network or community features
- Coffee journal / personal brew tracking
- Personalized recommendation engine
- Brewing calculator
- Full Colombia-wide interactive map
- Large-scale coffee database
- Interactive laboratory / brewing simulation mode

These can become future product directions once the core visual learning experience has been validated.

## Future product directions

The MVP should be designed so the product could later expand into several visual modes:

### Coffee Tree

A connected visual structure showing relationships between coffee plant, variety, environment, processing, roasting, brewing, and flavor.

### Regional Map

An interactive exploration of coffee-producing areas, farms, environments, and regional differences.

### Interactive Lab

A simulation where users change variables such as grind, temperature, ratio, roast, or processing and observe how the expected sensory result changes.

### Visual Journey

The initial and primary MVP mode: an immersive story around one coffee.

## Product principle

**Teach through relationships, not isolated facts.**

The user should leave each journey with a mental model of *why* the coffee tastes the way it does, not simply a list of facts about the coffee.

## MVP definition in one sentence

> **An immersive visual experience where you explore coffees from Colombia's Eje Cafetero and discover the chain of factors that make each coffee taste different.**
