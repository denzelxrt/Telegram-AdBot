import os
import toml
import logging
import asyncio

from telethon import TelegramClient
from telethon import functions, types, errors, events

from tabulate import tabulate

logging.basicConfig(
	level=logging.INFO,
	format="\x1b[38;5;147m[\x1b[0m%(asctime)s\x1b[38;5;147m]\x1b[0m %(message)s",
	datefmt="%H:%M:%S"
)
logging.getLogger("telethon").setLevel(level=logging.CRITICAL)

class Telegram():

	def __init__(self):
		os.system("cls && title ")
		
		with open("assets/config.toml") as f:
			self.config = toml.loads(f.read())
			
		with open("assets/groups.txt", encoding="utf-8") as f:
			self.groups = [i.strip() for i in f]
			
		self.phone_number = self.config["telegram"]["phone_number"]
		self.api_id = self.config["telegram"]["api_id"]
		self.api_hash = self.config["telegram"]["api_hash"]
		
		self.client = TelegramClient(
			session="assets/sessions/%s" % (self.phone_number),
			api_id=self.api_id,
			api_hash=self.api_hash
		)
		
		self.promotions_chat = None
		self.forward_message = None
		
	def tablize(self, headers: list, data: list):
		print(
			tabulate(
				headers=headers,
				tabular_data=data
			).replace("-", "\x1b[38;5;147m-\x1b[0m")
		)

	async def connect(self):
		await self.client.connect()
		logging.info("Attempting to login \x1b[38;5;147m(\x1b[0m%s\x1b[38;5;147m)\x1b[0m" % (self.phone_number))

		if not await self.client.is_user_authorized():
			logging.info("Verification code required \x1b[38;5;147m(\x1b[0m%s\x1b[38;5;147m)\x1b[0m" % (self.phone_number))
			await self.client.send_code_request(self.phone_number)
			logging.info("Sent verification code \x1b[38;5;147m(\x1b[0m%s\x1b[38;5;147m)\x1b[0m" % (self.phone_number))

			await self.client.sign_in(self.phone_number, input("\x1b[38;5;147m[\x1b[0m?\x1b[38;5;147m]\x1b[0m Verification code\x1b[38;5;147m:\x1b[0m "))

		self.user = await self.client.get_me()
		logging.info("Successfully signed into account \x1b[38;5;147m(\x1b[0m%s\x1b[38;5;147m)\x1b[0m" % (self.user.username))

	async def get_groups(self):
		reply = []

		results = await self.client.get_dialogs(
			limit=None
		)

		for dialog in results:
			if dialog.is_group and dialog.is_channel:
				reply.append(dialog)

		return reply

	async def get_all_chats(self):
		results = await self.client(functions.messages.GetDialogsRequest(
			offset_date=None,
			offset_id=0,
			offset_peer=types.InputPeerEmpty(),
			limit=200,
			hash=0
		))        
		return results.chats

	async def get_chat_messages(self):
		results = []
		
		async for message in self.client.iter_messages(self.promotions_chat):
			if message.text != None: results.append(message)
		
		return results

	async def clean_send(self, group: types.Channel):
		try:
			await self.client.forward_messages(group, self.forward_message)
			return True
		except errors.FloodWaitError as e:
			logging.info("Ratelimited for \x1b[38;5;147m%s\x1b[0ms." % (e.seconds))
			await asyncio.sleep(int(e.seconds))
		except Exception as e:
			return e

	async def cycle(self):
		while True:
			try:
				groups = await self.get_groups()
				for group in groups:
					try:
						last_message = (await self.client.get_messages(group, limit=1))[0]
						if last_message.from_id.user_id == self.user.id:
							logging.info("Skipped \x1b[38;5;147m%s\x1b[0m as our message is the latest." % (group.title))
							continue
						
						if await self.clean_send(group):
							logging.info("Forwarded your message to \x1b[38;5;147m%s\x1b[0m!" % (group.title))
						else:
							logging.info("Failed to forward your message to \x1b[38;5;147m%s\x1b[0m!" % (group.title))
						
						await asyncio.sleep(self.config["sending"]["send_interval"])
					except Exception:
						pass
			except Exception:
				pass
				
			await asyncio.sleep(self.config["sending"]["loop_interval"])

	async def join_groups(self):
		seen = []
		
		option = input("\x1b[38;5;147m[\x1b[0m?\x1b[38;5;147m]\x1b[0m Join groups?\x1b[38;5;147m:\x1b[0m ").lower()
		if option == "" or "n" in option: return
		print()
		
		for invite in self.groups:
			if invite in seen: continue
			seen.append(seen)
			
			while True:
				try:
					if "t.me" in invite: code = invite.split("t.me/")[1]
					else: code = invite
					
					await self.client(functions.channels.JoinChannelRequest(code))
					logging.info("Successfully joined \x1b[38;5;147m%s\x1b[0m!" % (invite))
					break
				except errors.FloodWaitError as e:
					logging.info("Ratelimited for \x1b[38;5;147m%s\x1b[0ms." % (e.seconds))
					await asyncio.sleep(int(e.seconds))
				except Exception:
					logging.info("Failed to join \x1b[38;5;147m%s\x1b[0m." % (invite))
					break
			
			await asyncio.sleep(0.8)

	async def start(self):
		await self.connect()
		
		print()
		await self.join_groups()
		print()
		
		groups = await self.get_all_chats()
		self.tablize(
			headers=["ID", "Name"],
			data=[[group.id, group.title] for group in groups]
		)
		print()
		
		logging.info("Please select the group you would like to forward the message from")
		channel_id = int(input("\x1b[38;5;147m[\x1b[0m?\x1b[38;5;147m]\x1b[0m ID\x1b[38;5;147m:\x1b[0m "))
		
		for group in groups:
			if group.id == channel_id:
				self.promotions_chat = group
				
		if self.promotions_chat == None: return logging.info("Invalid chat ID selected.")
		print()
		
		logging.info("Selected \x1b[38;5;147m%s\x1b[0m as your promotions chat." % (self.promotions_chat.title))
		print()
		
		messages = await self.get_chat_messages()
		self.tablize(
			headers=["ID", "Content"],
			data=[[message.id, message.text[:50]] for message in messages]
		)
		print()
		
		logging.info("Please select the message you would like to forward")
		message_id = int(input("\x1b[38;5;147m[\x1b[0m?\x1b[38;5;147m]\x1b[0m ID\x1b[38;5;147m:\x1b[0m "))
		
		for message in messages:
			if message.id == message_id:
				self.forward_message = message
				
		if self.forward_message == None: return logging.info("Invalid message ID selected.")
		print()
		
		logging.info("Selected \x1b[38;5;147m%s\x1b[0m are your message to forward." % (self.forward_message.text[:50]))        
		groups = await self.get_groups()
		logging.info("Sending out your message to \x1b[38;5;147m%s\x1b[0m groups!" % (len(groups)))
		
		print()
		await self.cycle()
		
if __name__ == "__main__":
	client = Telegram()
	asyncio.get_event_loop().run_until_complete(client.start())
