Welcome to the Auction Discord Bot

Developed for the PST division of RD2L, this bot handles the live player draft at the start of every new PST season.

The draft begins with the first captain in the list nominating a player, and these nomination rounds will continue until the playerlist is empty. If a captain does not nominate a player in time, the autonominator will select the highest remaining MMR player to be bid upon. Bidding starts off with 60 initial seconds (after a brief buffer phase so captains can see the player's information) and is reset after each bid. The timer decreases on subsequent bids. There are 4 'breaks' in the draft. These occur every PlayerCount/CaptainCount bidding rounds.

Important Info:
- If captains are 'tied' for a player, the winner of that bid will be determined randomly.
- If no captains bid on a player, the nominating captain will win the player (including autonominations).
- Successful nominations and bids will result in a thumbs up bot reaction, thumbs down otherwise.

To download and run locally: 
- Ensure that you have a native version of python > 3.8.
- Install the dependencies found in the requirements.txt.
- Add your discord ID to the ADMIN_IDS list found in draft.py.
- Add the desired channel name to the GENERIC_DRAFT_CHANNEL_NAMES list found in auction.py.
- Adjust the timers in auction.py and lot.py to suit your needs.
- Ensure your player and captain csv's are correctly formatted (examples can be found above; IMPORTANT: CAPTAIN NAMES MUST BE THEIR DISCORD NAMES).
- Create a new project/db on replit.com. In the console, type 'env' and press enter. Find the REPLIT_DB_URL.
- Create a discord bot through the discord developer portal, and invite it to your server (make sure to copy the token).
- Create a .env file in the project directory. Add the REPLIT_DB_URL and the DISCORD_AUTH_TOKEN variables to it.
- After all that is completed, run 'python draft.py' to get your player/captain lists in the DB, and 'python auction.py' to start the bot.

Basic Commands:
- !nominate - Nominates a player
- !bid x - Bids x amount on a player

Admin Commands (bot will only recognize users with ID's in the ADMIN_IDS list): 
- !start - starts the draft
- !playerlist - prints out an embed with the list of players
- !captainlist - prints out an embed with the list of captains
- !undo - reverts the last nomination/bidding round (useful for user error or the latency bug causing confusion when a captain nominates right as the autonominator does)
- !teams - prints out a list of captains and their current teams
- !DELETE - deletes the current database, will have to run 'python draft.py' and restart the bot after this to get your DB repopulated.
- !pause - pauses the draft
- !resume - resumes the draft
- !playerinfo x - prints out information of x player
- !player x - adds x player to the DB
- !captain x - adds x captain to the db

If you have any questions or concerns, or would like to help improve upon the bot, please reach out to me!