import sc2
from sc2 import maps, Difficulty, run_game, Race
from sc2.constants import NEXUS, PYLON, PROBE, ASSIMILATOR, CYBERNETICSCORE, \
GATEWAY, STALKER, ZEALOT
from sc2.player import Bot, Computer

class dumbot(sc2.BotAI):
	async def on_step(self, iteration):
		await self.distribute_workers()
		await self.create_probes()
		await self.create_pylons()
		await self.create_assimilators()
		await self.create_army_buildings()
		await self.create_army_units()
		await self.expand()

	async def create_probes(self):
		for nexus in self.units(NEXUS).ready.noqueue:
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
			if self.units(GATEWAY).ready.exists:
				if not self.units(CYBERNETICSCORE).ready.exists and \
				self.can_afford(CYBERNETICSCORE) and \
				not self.already_pending(CYBERNETICSCORE):
					await self.build(CYBERNETICSCORE, near=dest_pylon)
			else:
				if self.can_afford(GATEWAY) and not self.already_pending(GATEWAY):
					await self.build(GATEWAY, near=dest_pylon)


	async def create_army_units(self):
		if self.units(CYBERNETICSCORE).ready.exists:
			for gw in self.units(GATEWAY).ready.noqueue:
				if self.can_afford(ZEALOT) and self.supply_left > 0 and self.units(ZEALOT).amount < 10:
					await self.do(gw.train(ZEALOT))
				if self.can_afford(STALKER) and self.supply_left > 0:
					await self.do(gw.train(STALKER))


	async def expand(self):
		if self.units(NEXUS).amount < 3 and self.can_afford(NEXUS):
			await self.expand_now()


run_game(maps.get("AbyssalReefLE"),[
		Bot(Race.Protoss, dumbot()),
		Computer(Race.Terran, Difficulty.Easy)
	], realtime=False)