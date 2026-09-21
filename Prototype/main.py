#Zombie Game Prototype 1
#Start Date: 9/14/26
import random, time

#Gets user input for the num of Zombies and Humans
total_human_pop = int(input("Please enter the number of 'Humans' for the simulation: "))
total_zombie_pop = int(input("Please enter the number of 'Zombies' for the simulation: "))
zombie_health = 5
human_health = 10
passed_iterations = 1

#Variables related to the simulation runtime.
iterations = int(input("Please enter the number of iterations the simulation should run: "))
runtime = int(input("How long would you like each simulation to run for?(Seconds): "))
def actions(x, y, z, x2):
    passed_iterations = 0
    for x in range(0, x):
        print("---------------------------------------")
        print("SIMULATION ", x + 1)
        print("---------------------------------------")
        for y in range (0, y):
            time.sleep(1)
            human_roll_num = random.randint(1,5)
            zombie_roll_num = random.randint(1,5)
        
            if zombie_roll_num == human_roll_num:
                print("Zombie and Human are at a stand-still.")

            elif zombie_roll_num > human_roll_num:
                zombie_damage = random.randint(1,3)
                print("Zombie has gained the advantage over the human.")
                print("Zombie has dealt ", zombie_damage, " damage to the human.")
                x2 -= zombie_damage

            else:
                human_damage = random.randint(1,5)
                print("Human has gained the advantage over the zombie")
                print("Human has dealt ", human_damage, " damage to the zombie.")
                z -= human_damage

            y += 1
        x += 1
        passed_iterations += 1

#Function to run the simulation
def simulation_run(a, b, c, d, e, f):
        #Sets the total hp for all zombies and humans in the sim. The count of the total humans/zombies is reduced by 1 whenever
        #the total population HP is reduced by the HP of a single zombie or human.
        zombie_hp_total = b * e
        human_hp_total = a * f

        
        while a != 0 or b != 0 or passed_iterations != c:
            actions(iterations, runtime, zombie_health, human_health)
            #Adds win condition for zombies and humans.
            if total_human_pop == 0:
                 print("Humans win! There are currently ", total_human_pop, " humans left.")
            elif human_health == 0:
                 print("Zombies win! There are currently ", total_zombie_pop, " zombies left.")                 
            
    
simulation_run(total_human_pop, total_zombie_pop, iterations, runtime, zombie_health, human_health)