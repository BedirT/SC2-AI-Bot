import sc2
from sc2 import maps, Difficulty, run_game, Race, position
from sc2.constants import NEXUS, PYLON, PROBE, ASSIMILATOR, CYBERNETICSCORE, \
GATEWAY, STALKER, ZEALOT, STARGATE, VOIDRAY, ROBOTICSFACILITY, OBSERVER
from sc2.player import Bot, Computer

import random
import numpy as np
import cv2

class dumbot(sc2.BotAI):

	def __init__(self):
		self.ITERATIONS_PER_MINUTE = 165
		self.MAX_WORKERS = 65

	async def on_step(self, iteration):
		self.iteration = iteration
		await self.scout()
		await self.distribute_workers()
		await self.create_probes()
		await self.create_pylons()
		await self.create_assimilators()
		await self.create_army_buildings()
		await self.create_army_units()
		await self.expand()
		await self.intel()
		await self.attack()

	async def intel(self):
		game_data = np.zeros((self.game_info.map_size[1], self.game_info.map_size[0], 3), np.uint8)

		draw_dict = {
		NEXUS: [15, (0, 255, 0)],
		PYLON: [3, (20, 235, 0)],
		PROBE: [1, (55, 200, 0)],
		ASSIMILATOR: [2, (55, 200, 0)],
		GATEWAY: [3, (200, 100, 0)],
		CYBERNETICSCORE: [3, (150, 150, 0)],
		STARGATE: [5, (255, 0, 0)],
		ROBOTICSFACILITY: [5, (215, 155, 0)],
		VOIDRAY: [3, (255, 100, 0)]
		}

		for unit_type in draw_dict:
			for unit in self.units(unit_type).ready:
				pos = unit.position
				cv2.circle(game_data, (int(pos[0]), int(pos[1])), draw_dict[unit_type][0], draw_dict[unit_type][1], -1)

		main_base_names = ["nexus", "commandcenter", "hatchery"]
		for enemy_building in self.known_enemy_structures:
			pos = enemy_building.position
			if enemy_building.name.lower() not in main_base_names:
				cv2.circle(game_data, (int(pos[0]), int(pos[1])), 5, (200, 50, 212), -1)
		for enemy_building in self.known_enemy_structures:
			pos = enemy_building.position
			if enemy_building.name.lower() in main_base_names:
				cv2.circle(game_data, (int(pos[0]), int(pos[1])), 15, (0, 0, 255), -1)

		for enemy_unit in self.known_enemy_units:

			if not enemy_unit.is_structure:
				worker_names = ["probe", "scv", "drone"]
				pos = enemy_unit.position
				if enemy_unit.name.lower() in worker_names:
					cv2.circle(game_data, (int(pos[0]), int(pos[1])), 1, (55, 0, 155), -1)
				else:
					cv2.circle(game_data, (int(pos[0]), int(pos[1])), 3, (50, 0, 215), -1)

			for obs in self.units(OBSERVER).ready:
				pos = obs.position
				cv2.circle(game_data, (int(pos[0]), int(pos[1])), 1, (255, 255, 255), -1)

		flipped = cv2.flip(game_data, 0)
		resized = cv2.resize(flipped, dsize=None, fx=2, fy=2)

		cv2.imshow('Intel', resized)
		cv2.waitKey(1)

	def random_location_variance(self, enemy_start_location):
		x = enemy_start_location[0]
		y = enemy_start_location[1]

		x += ((random.randrange(-20, 20))/100) * enemy_start_location[0]
		y += ((random.randrange(-20, 20))/100) * enemy_start_location[1]

		if x < 0:
		    x = 0
		if y < 0:
		    y = 0
		if x > self.game_info.map_size[0]:
		    x = self.game_info.map_size[0]
		if y > self.game_info.map_size[1]:
		    y = self.game_info.map_size[1]

		go_to = position.Point2(position.Pointlike((x,y)))
		return go_to

	async def scout(self):
		if len(self.units(OBSERVER)) > 0:
			scout = self.units(OBSERVER)[0]
			if scout.is_idle:
				enemy_location = self.enemy_start_locations[0]
				move_to = self.random_location_variance(enemy_location)
				# print(move_to)
				await self.do(scout.move(move_to))

		else:
			for rf in self.units(ROBOTICSFACILITY).ready.noqueue:
				if self.can_afford(OBSERVER) and self.supply_left > 0:
					await self.do(rf.train(OBSERVER))


	async def create_probes(self):
		for nexus in self.units(NEXUS).ready.noqueue:
			probes_amount = self.units(PROBE).amount
			if (self.units(NEXUS).amount * 20) > probes_amount and probes_amount < self.MAX_WORKERS:
				if self.can_afford(PROBE):
					await self.do(nexus.train(PROBE))

	async def create_pylons(self):
		if self.supply_left < 5 and not self.already_pending(PYLON):
			nexusS = self.units(NEXUS).ready
			if nexusS.exists and self.can_afford(PYLON):
				await self.build(PYLON, near=nexusS.first)

	async def create_assimilators(self):
		for nexus in self.units(NEXUS).ready:
			pos_vespines = self.state.vespene_geyser.closer_than(10.0, nexus)
			for vespene in pos_vespines:
				worker = self.select_build_worker(vespene.position)
				if self.can_afford(ASSIMILATOR) and worker is not None: 
					if not self.units(ASSIMILATOR).closer_than(1.0, vespene).exists:
						await self.do(worker.build(ASSIMILATOR, vespene))

	async def create_army_buildings(self):
		if self.units(PYLON).ready.exists:
			dest_pylon = self.units(PYLON).ready.random
			if self.units(GATEWAY).ready.exists and not self.units(CYBERNETICSCORE):
				if self.can_afford(CYBERNETICSCORE) and \
				not self.already_pending(CYBERNETICSCORE):
					await self.build(CYBERNETICSCORE, near=dest_pylon)
			
			elif self.units(GATEWAY).ready.amount < 1:
				if self.can_afford(GATEWAY) and not self.already_pending(GATEWAY):
					await self.build(GATEWAY, near=dest_pylon)

			if self.units(CYBERNETICSCORE).ready.exists:
				if len(self.units(ROBOTICSFACILITY)) < 1:
					if self.can_afford(ROBOTICSFACILITY) and not self.already_pending(ROBOTICSFACILITY):
						await self.build(ROBOTICSFACILITY, near=dest_pylon)

			if self.units(CYBERNETICSCORE).ready.exists and len(self.units(STARGATE)) < (self.iteration / self.ITERATIONS_PER_MINUTE):
				if self.can_afford(STARGATE) and not self.already_pending(STARGATE):
					await self.build(STARGATE, near=dest_pylon)




	async def create_army_units(self):
		if self.units(CYBERNETICSCORE).ready.exists:
			for sg in self.units(STARGATE).ready.noqueue:
				if self.can_afford(VOIDRAY) and self.supply_left > 0:
					await self.do(sg.train(VOIDRAY))



	def find_target(self, state):
		if len(self.known_enemy_units) > 0:
			return random.choice(self.known_enemy_units)
		elif len(self.known_enemy_structures) > 0:
			return random.choice(self.known_enemy_buildings)
		else:
			return self.enemy_start_locations[0]

	async def attack(self):

		army_units = { VOIDRAY: [8	, 3] }

		for UNIT_NAME in army_units:
			if self.units(UNIT_NAME).amount > army_units[UNIT_NAME][0] and self.units(UNIT_NAME).amount > army_units[UNIT_NAME][1]:
				for u in self.units(UNIT_NAME).idle:
					await self.do(u.attack(self.find_target(self.state)))

			elif self.units(UNIT_NAME).amount > army_units[UNIT_NAME][1]:
				if len(self.known_enemy_units) > 0:
					for u in self.units(UNIT_NAME).idle:
						await self.do(u.attack(random.choice(self.known_enemy_units)))

	async def expand(self):
		if self.units(NEXUS).amount < (self.iteration / self.ITERATIONS_PER_MINUTE) and self.can_afford(NEXUS):
			await self.expand_now()


run_game(maps.get("AbyssalReefLE"),[
		Bot(Race.Protoss, dumbot()),
		Computer(Race.Terran, Difficulty.Hard)
	], realtime=False)