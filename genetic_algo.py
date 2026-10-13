import random

POP_SIZE = 30
GENERATIONS = 60
MUTATION_RATE = 0.12
# 0 = VM1
# 1 = VM2
NODES = ["VM1", "VM2"]
MIGRATION_TIME_SEC = 30
MIGRATION_COST_PER_SEC = 0.002
CURRENT_NODE = 0
def normalize(value, minimum, maximum):
  if maximum == minimum:
    return 0.0
  value = (value - minimum) / (maximum - minimum)
  return max(0.0, min(1.0, value))
 
def migration_penalty(plan):
  switches = 0
  for i in range(1, len(plan)):
    if plan[i] != plan[i - 1]:
      switches += 1
  return switches * MIGRATION_TIME_SEC * MIGRATION_COST_PER_SEC

def fitness(plan, forecast):
  total_score = 0.0
  for step, node_index in enumerate(plan):
    node = NODES[node_index]
    state = forecast[node][step]
    price = state["price"]
    cpu = state["cpu"]
    ram = state["ram"]
    network = state["network_mbps"]
    price_score = normalize(
      price,
      0,
      20
    )
    cpu_score = normalize(
      cpu,
      0,
      100
    )
    ram_score = normalize(
      ram, 
      0,
      100
    )
    network_score = normalize(
      network,
      0,
      100
    )
    step_cost = (
      price_score * 0.40 + cpu_score * 0.25 + ram_score * 0.25 + network_score * 0.10
    )
    total_score += step_cost 
  total_score += migration_penalty(plan) * 0.10
  return -total_score

def create_population(steps):
  population = []
  for _ in range(POP_SIZE):
    plan = [
       random.randint(0,1)
       for _ in range(steps)
    ]
    population.append(plan)
  return population

def select_parents(population, forecast):
   scored = sorted(
    population,
    key=lambda plan: fitness(plan, forecast),
    reverse=True
   )
   return scored[:POP_SIZE // 2]

def crossover(parent1, parent2):
   if len(parent1) <= 1:
     return parent1.copy()
   cut = random.randint(
     1,
     len(parent1) - 1
   )
   child = (
     parent1[:cut]
     + parent2[cut:]
   )
   return child 

def mutate(plan):
   for i in range(len(plan)):
     if random.random() < MUTATION_RATE:
       plan[i] = random.randint(0,1)
   return plan

def run_ga(forecast):
   steps = len(forecast["VM1"])
   population = create_population(steps)
   print("\nRunning Genetic Algorithm...")
   print(f"Population : {POP_SIZE}")
   print(f"generations : {GENERATIONS}")
   print(f"mutation : {MUTATION_RATE}")
   print(f"Forecast steps : {steps}")
   for generation in range(GENERATIONS):
     parents = select_parents(
       population,
       forecast
     )
     children = []
     while len(children) < POP_SIZE // 2:
        parent1, parent2 = random.sample(
          parents,
          2
        )
        child = crossover(
          parent1,
          parent2
        )
        child = mutate(child)
        children.append(child)
     population = parents + children
     if generation % 10 == 0:
       best_plan = max(
         population,
         key=lambda plan:fitness(
            plan,
            forecast
         )
       )
       best_fitness = fitness(
          best_plan,
          forecast
       )

       print(
         f"Generation {generation:3d}"
         f" -> Fitness: {best_fitness:.4f}"
       )
   best_plan = max(
      population,
      key=lambda plan: fitness(
          plan, 
          forecast
      )
   )
   return best_plan

def analyze_plan(plan):
  vm1_steps = plan.count(0)
  vm2_steps = plan.count(1)
  switches = sum(
    1
    for i in range(1, len(plan))
    if plan[i] != plan[i - 1]
  )
  recommended_node = plan[0]
  initial_migration = (
    CURRENT_NODE != recommended_node
  )
  total_migrations = switches 
  if initial_migration:
    total_migrations += 1
  migration_cost = (
    total_migrations  * MIGRATION_TIME_SEC * MIGRATION_COST_PER_SEC)
  
  print("\n" + "=" * 60)
  print("GENETIC ALGORITHM RESULT")
  print("=" * 60)
  print("\nOptimized plan:")
  for step, node_index in enumerate(plan):
    print(
       f"step {step + 1:2d} -> "
       f"{NODES[node_index]}"
    )
  print("\nDistribution:")
  print(f"VM1: {vm1_steps} steps")
  print(f"VM2: {vm2_steps} steps")
  print(f"\nCurrent node: {NODES[CURRENT_NODE]}")
  print(f"Recommended node: {NODES[recommended_node]}")
  print(
       f"\nInitial Migration:"
       f"{'YES' if initial_migration else 'NO'}"
  )
  print(f"\nTotal migrations: {total_migrations}")
  
  print(f"Migration cost: "
        f"${migration_cost:.4f}"
  )
  print("\nDecision:")
  if initial_migration:
   print(
     f"MIGRATE "
     f"{NODES[CURRENT_NODE]} -> "
     f"{NODES[recommended_node]}")
  else:
   print(f"STAY ON {NODES[CURRENT_NODE]}")
  print("=" * 60)

  
if __name__ == "__main__":
  forecast = {
    "VM1": [
       {
          "price": 12.0,
          "cpu": 45,
          "ram": 50,
          "network_mbps": 5
        },
        {
          "price": 13.0,
          "cpu": 55,
          "ram": 55,
          "network_mbps": 6
        },
        {
          "price": 15.0,
          "cpu": 70,
          "ram": 65,
          "network_mbps": 8
        },
        {
          "price": 17.0,
          "cpu": 80,
          "ram": 72,
          "network_mbps": 10
        },
        {
          "price": 18.0,
          "cpu": 85,
          "ram": 78,
          "network_mbps": 10
        }
    ],
    "VM2": [
        {
           "price": 10.0,
           "cpu": 30,
           "ram": 40,
           "network_mbps": 4
         },
         {
           "price": 10.5,
           "cpu": 32,
           "ram": 42,
           "network_mbps": 4
         },
         {
           "price": 11.0,
           "cpu": 35,
           "ram": 44,
           "network_mbps": 4
         },
         {
           "price": 11.5,
           "cpu": 38, 
           "ram": 45,
           "network_mbps": 5
          },
          {
            "price": 12.0,
            "cpu": 40,
            "ram": 47,
            "network_mbps": 6
           }
    ]
 }
best_plan = run_ga(forecast)
analyze_plan(best_plan)
