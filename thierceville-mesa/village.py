import math
import random
import numpy as np
from collections import defaultdict

import uuid
import mesa
import numpy
import pandas
from mesa import space
from mesa.batchrunner import BatchRunner
from mesa.datacollection import DataCollector
from mesa.time import RandomActivation
from mesa.visualization.ModularVisualization import ModularServer, VisualizationElement
from mesa.visualization.modules import ChartModule

class ContinuousCanvas(VisualizationElement):
    local_includes = [
        "./js/simple_continuous_canvas.js",
    ]

    def __init__(self, canvas_height=500,
                 canvas_width=500, instantiate=True):
        self.canvas_height = canvas_height
        self.canvas_width = canvas_width
        self.identifier = "space-canvas"
        if (instantiate):
            new_element = ("new Simple_Continuous_Module({}, {},'{}')".
                           format(self.canvas_width, self.canvas_height, self.identifier))
            self.js_code = "elements.push(" + new_element + ");"

    def portrayal_method(self, obj):
        return obj.portrayal_method()

    def render(self, model):
        representation = defaultdict(list)
        for obj in model.schedule.agents:
            portrayal = self.portrayal_method(obj)
            if portrayal:
                portrayal["x"] = ((obj.pos[0] - model.space.x_min) /
                                  (model.space.x_max - model.space.x_min))
                portrayal["y"] = ((obj.pos[1] - model.space.y_min) /
                                  (model.space.y_max - model.space.y_min))
            representation[portrayal["Layer"]].append(portrayal)
        return representation

def wander(x, y, speed, model):
    r = random.random() * math.pi * 2
    new_x = max(min(x + math.cos(r) * speed, model.space.x_max), model.space.x_min)
    new_y = max(min(y + math.sin(r) * speed, model.space.y_max), model.space.y_min)

    return new_x, new_y

class  Village(mesa.Model):
    def  __init__(self,  n_villagers, n_werewolves, n_clerics, n_hunters, counter):
        mesa.Model.__init__(self)
        self.space = mesa.space.ContinuousSpace(600, 600, False)
        self.schedule = RandomActivation(self)
        self.graphdata = DataCollector(counter)
        for  _  in  range(n_villagers):
            self.schedule.add(Villager(random.random()  *  600,  random.random()  *  600,  10, uuid.uuid1(), self))
        for  _  in  range(n_werewolves):
            self.schedule.add(Villager(random.random()  *  600,  random.random()  *  600,  10, uuid.uuid1(), self, villager_class="Werewolf"))
        for  _  in  range(n_clerics):
            self.schedule.add(Villager(random.random()  *  600,  random.random()  *  600,  10, uuid.uuid1(), self, villager_class="Cleric"))
        for  _  in  range(n_hunters):
            self.schedule.add(Villager(random.random()  *  600,  random.random()  *  600,  10, uuid.uuid1(), self, villager_class="Hunter"))
    def step(self):
        self.schedule.step()
        self.graphdata.collect(self)
        if self.schedule.steps >= 1000000:
            self.running = False

class Villager(mesa.Agent):
    def __init__(self, x, y, speed, unique_id: int, model: Village, distance_attack=40, p_attack=0.6, villager_class = "Villager"):
        super().__init__(unique_id, model)
        self.pos = (x, y)
        self.speed = speed
        self.model = model
        self.distance_attack = distance_attack
        self.p_attack = p_attack
        self.villager_class = villager_class
        self.transformed = False

    def portrayal_method(self):
        if self.villager_class == "Werewolf":
            color = "red"
        elif self.villager_class == "Cleric":
            color = "green"
        elif self.villager_class == "Hunter":
            color = "black"
        else:
            color = "blue"
        r = 6 if self.transformed else 3
        portrayal = {"Shape": "circle",
                     "Filled": "true",
                     "Layer": 1,
                     "Color": color,
                     "r": r}
        return portrayal

    def find_target(self, agents, villager_class ,distance):
        targets = []
        for agent in agents:
            if agent.villager_class == villager_class and (agent.pos[0]-self.pos[0])**2 + (agent.pos[1]-self.pos[1])**2 <= distance**2:
                targets.append(agent)
        return targets

    def step(self):
        self.pos = wander(self.pos[0], self.pos[1], self.speed, self.model)
        if self.villager_class == "Werewolf" and random.random() < 0.1:
            self.transformed = not self.transformed
        elif self.villager_class == "Cleric":
            targets = self.find_target(self.model.schedule.agents, "Werewolf", 30)
            for target in targets:
                if not target.transformed:
                    target.villager_class = "Villager"
        elif self.villager_class == "Hunter":
            targets = self.find_target(self.model.schedule.agents, "Werewolf", 40)
            for target in targets:
                if target.transformed:
                    self.model.schedule.remove(target)
        
        if self.transformed:
            targets = self.find_target(self.model.schedule.agents, "Villager", 40)
            for target in targets:
                target.villager_class = "Werewolf"
        

def run_single_server():
    villager_slider = mesa.visualization.ModularVisualization.UserSettableParameter(
        'slider', "Villagers", 25, 0, 50, 1)
    werewolf_slider = mesa.visualization.ModularVisualization.UserSettableParameter(
        'slider', "Werewolves", 5, 0, 50, 1)
    cleric_slider = mesa.visualization.ModularVisualization.UserSettableParameter(
        'slider', "Clerics", 1, 0, 5, 1)
    hunter_slider = mesa.visualization.ModularVisualization.UserSettableParameter(
        'slider', "Hunters", 1, 0, 50, 1)

    server = ModularServer(Village, [ContinuousCanvas(), ChartModule([{"Label": "Population", "Color": "orange"}, {"Label": "Werewolves", "Color": "red"}, {"Label": "Transformed werewolves", "Color": "purple"}], data_collector_name="graphdata")], "Village", {
                           "n_villagers":  villager_slider, "n_werewolves": werewolf_slider, "n_clerics": cleric_slider, "n_hunters": hunter_slider, "counter": counter})
    server.port = 8521
    server.launch()


def run_batch():
    batch_dict = {"n_villagers": [50], "n_werewolves": [
        5], "n_clerics": range(0, 6, 1), "n_hunters": [1]}
    batch_run = BatchRunner(Village, batch_dict, fixed_parameters={"counter": counter}, model_reporters=counter)
    batch_run.run_all()
    return batch_run.get_model_vars_dataframe()


if __name__ == "__main__":
    counter = {"Population": lambda m: len(m.schedule.agents)}
    counter["Werewolves"] = lambda m: len([agent for agent in m.schedule.agents if agent.villager_class == "Werewolf"])
    counter["Transformed werewolves"] = lambda m: len([agent for agent in m.schedule.agents if agent.transformed == True])

    print(run_batch())