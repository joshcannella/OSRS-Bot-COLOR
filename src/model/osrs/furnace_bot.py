import time
from typing import NamedTuple

import utilities.api.item_ids as ids
import utilities.color as clr
import utilities.imagesearch as imsearch
from model.osrs.osrs_bot import OSRSBot
from utilities.api.morg_http_client import MorgHTTPSocket
# from utilities.api.status_socket import StatusSocket
from utilities.geometry import Rectangle

# materials
GOLD_BAR_NAME = "Gold bar"
SAPPHIRE_NAME = "Sapphire"
# crafted items
GOLD_AMULET_U_NAME = "Gold amulet (u)"
SAPPHIRE_RING_NAME = "Sapphire ring"

class Item(NamedTuple):
    """Represents an item in the game."""

    name: str
    id: int


class CraftItem:
    """
    Represents an item that can be crafted.

    Attributes:
        item (Item): The item to be crafted.
        materials (list): The materials required for crafting the item.
    """

    def __init__(self, item: Item):
        self.item = item
        self.materials = self.__init_materials()

    def __init_materials(self) -> list:
        """
        Initializes and returns the materials required for crafting the item.

        Returns:
            list: The materials required for crafting the item.
        """
        if self.item.id == ids.GOLD_AMULET_U:
            return [Item(name=GOLD_BAR_NAME, id=ids.GOLD_BAR)]
        elif self.item.id == ids.SAPPHIRE_RING:
            return [
                Item(name=GOLD_BAR_NAME, id=ids.GOLD_BAR),
                Item(name=SAPPHIRE_NAME, id=ids.SAPPHIRE)
                ]
        else:
            return []


class OSRSFurnaceBot(OSRSBot):
    """
    A class representing a bot that crafts/smelts items at a furnace in the game Old School RuneScape.

    Attributes:
    - bot_title (str): The title of the bot.
    - description (str): A description of the bot.
    - running_time (int): The duration in minutes for which the bot will run.
    - craft_item (CraftItem): The item that the bot will craft/smith at the furnace.
    - bank (Bank): The bank object in the game.
    - furnace (Furnace): The furnace object in the game.
    - options_set (bool): A flag indicating whether the options for the bot have been set.

    Methods:
    - __init__(self): Initializes a new instance of the OSRSFurnaceBot class.
    - create_options(self): Creates the options for the bot using the OptionsBuilder.
    - save_options(self, options: dict): Saves the selected options as properties of the bot.
    - main_loop(self): The main loop of the bot where the crafting/smelting actions are performed.
    - __init_craft_item(self, item_name: str) -> CraftItem | None: Initializes a CraftItem object based on the selected item name.
    - __logout(self, msg): Logs out the bot and stops its execution.
    - __retry(self, action_func, on_retry_func=None, retry_seconds: int = 10): Retries an action function with a specified retry interval.
    - __click_on_furnace(self) -> bool: Clicks on the furnace object in the game.
    - __click_on_bank(self) -> bool: Clicks on the bank object in the game.
    - __exit_bank(self): Exits the bank UI in the game.
    """
    def __init__(self):
        bot_title = "Furnace Bot"
        description = "Crafts/smelts items at a furnace."
        super().__init__(bot_title=bot_title, description=description)
        # Set option variables below (initial value is only used during headless testing)
        self.running_time = 30
        self.craft_item = None
        self.bank = None
        self.furnace = None
        self.options_set = False

    def create_options(self):
        """
        Use the OptionsBuilder to define the options for the bot. For each function call below,
        we define the type of option we want to create, its key, a label for the option that the user will
        see, and the possible values the user can select. The key is used in the save_options function to
        unpack the dictionary of options after the user has selected them.
        """
        self.options_builder.add_slider_option("running_time", "How long to run (minutes)?", 30, 720)
        self.options_builder.add_dropdown_option("craft_item", "Craft Item", [GOLD_AMULET_U_NAME, SAPPHIRE_RING_NAME])

    def save_options(self, options: dict):
        """
        For each option in the dictionary, if it is an expected option, save the value as a property of the bot.
        If any unexpected options are found, log a warning. If an option is missing, set the options_set flag to
        False.
        """
        for option in options:
            if option == "running_time":
                self.running_time = options[option]
            elif option == "craft_item":
                self.craft_item = self.__init_craft_item(options[option])
            else:
                self.log_msg(f"Unknown option: {option}")
                print("Developer: ensure that the option keys are correct, and that options are being unpacked correctly.")
                self.options_set = False
                return
        self.log_msg(f"Running time: {self.running_time} minutes.")
        self.log_msg(f"Crafting item: {self.craft_item.item}.")
        self.log_msg("Options set successfully.")
        self.options_set = True

    def main_loop(self):
        """
        When implementing this function, you have the following responsibilities:
        1. If you need to halt the bot from within this function, call `self.stop()`. You'll want to do this
           when the bot has made a mistake, gets stuck, or a condition is met that requires the bot to stop.
        2. Frequently call self.update_progress() and self.log_msg() to send information to the UI.
        3. At the end of the main loop, make sure to call `self.stop()`.

        Additional notes:
        - Make use of Bot/RuneLiteBot member functions. There are many functions to simplify various actions.
          Visit the Wiki for more.
        - Using the available APIs is highly recommended. Some of all of the API tools may be unavailable for
          select private servers. For usage, uncomment the `api_m` and/or `api_s` lines below, and use the `.`
          operator to access their functions.
        """
        # Setup APIs
        api_m = MorgHTTPSocket()
        # api_s = StatusSocket()

        # select inventory tab
        self.log_msg("Selecting inventory...")
        self.mouse.move_to(self.win.cp_tabs[3].random_point())
        self.mouse.click()

        # Set state
        state = "pre-craft"  # pre-craft, craft, post-craft, bank
        available_slots = 28
        # Set this to True if you have a mould in your inventory (code assumes it's in slot 28)
        use_mould = True
        if use_mould:
            available_slots -= 1
        # Calculate max craftable: available_slots / materials required per craft
        max_craftable = available_slots // len(self.craft_item.materials)
        self.log_msg(f"Max craftable: {max_craftable}")
        last_craft_item_index = max_craftable - 1

        # Main loop
        start_time = time.time()
        end_time = self.running_time * 60
        while time.time() - start_time < end_time:
            # -- Perform bot actions here --

            self.log_msg(f"State: {state}")
            
            inv = api_m.get_inv()
            last_item = next((item for item in inv if item["index"] == last_craft_item_index), None)
            if last_item_id := last_item["id"] if last_item else None:
                self.log_msg(f"Last item id: {last_item_id}")
            else:
                self.__logout("Last item not found. idk what to do. logging out.")

            if state == "pre-craft":
                if last_item_id == self.craft_item.item.id:
                    self.log_msg("Crafting complete. Moving to bank.")
                    state = "post-craft"
                    # exit the loop and move to the next state
                    continue
                if self.__click_on_furnace() is False:
                    self.__logout("Furnace not found.")
                if self.__begin_crafting(self.craft_item.item):
                    state = "craft"
            elif state == "craft":
                if last_item_id == self.craft_item.item.id:
                    self.log_msg("Crafting complete. Moving to bank.")
                    state = "post-craft"
                else:
                    self.log_msg("Crafting...")
                    if api_m.get_is_player_idle():
                        self.log_msg("Player is idle.")
                        state = "pre-craft"
            elif state == "post-craft":
                # move to bank
                if self.__click_on_bank() is False:
                    self.__logout("Bank not found.")
                self.log_msg("Moving to bank...")
                time.sleep(10)
                state = "bank"
            elif state == "bank":
                # deposit all crafted items and withdraw materials

                # 1. deposit: click on craft item in inventory
                self.mouse.move_to(self.win.inventory_slots[4].random_point())
                self.mouse.click()
                time.sleep(1)

                # 2. withdraw: click on materials in bank
                for material in self.craft_item.materials:
                    file_name = f"{material.name.replace(' ', '_')}.png"
                    mat_img = imsearch.BOT_IMAGES.joinpath("items", file_name)
                    self.log_msg(f"Searching for {material.name}... ({file_name})")
                    if mat := imsearch.search_img_in_rect(mat_img, self.win.game_view, confidence=0.50):
                        self.mouse.move_to(mat.random_point())
                        self.mouse.click()
                        time.sleep(1)
                    else:
                        self.__logout(f"Material {material.name} not found.")
                    
                
                # 3. exit ui: click close icon
                self.__exit_bank()

                # 4. set state to pre-craft
                state = "pre-craft"
            # wait 1 second
            time.sleep(1)

            # Code within this block will LOOP until the bot is stopped.
            self.update_progress((time.time() - start_time) / end_time)

        self.update_progress(1)
        self.__logout("Finished.")
        self.stop()

    def __init_craft_item(self, item_name: str) -> CraftItem | None:
        if item_name == GOLD_AMULET_U_NAME:
            return CraftItem(Item(name=GOLD_AMULET_U_NAME, id=ids.GOLD_AMULET_U))
        elif item_name == SAPPHIRE_RING_NAME:
            return CraftItem(Item(name=SAPPHIRE_RING_NAME, id=ids.SAPPHIRE_RING))
        else:
            return None

    def __logout(self, msg):
        self.log_msg(msg)
        self.logout()
        self.stop()

    def __retry(self, action_func, on_retry_func=None, retry_seconds: int = 15):
        start_time = time.time()
        while time.time() - start_time < retry_seconds:
            if ret := action_func():
                return ret
            if on_retry_func:
                on_retry_func()
            time.sleep(1)
        return None

    def __click_on_furnace(self) -> bool:
        def retry_find_furnace():
            self.log_msg("Furnace obj not found... Trying again.")
            self.move_camera(90)

        if furnace_obj := self.__retry(lambda: self.get_nearest_tag(clr.PINK), retry_find_furnace):

            def find_furnace():
                self.mouse.move_to(furnace_obj.random_point())
                return self.mouseover_text(contains="Smelt", color=clr.OFF_WHITE)

            if self.__retry(find_furnace):
                self.mouse.click()
                return True
            else:
                self.log_msg("Could not find furnace.")
                return False
        else:
            return False

    def __click_on_bank(self) -> bool:
        def retry_find_bank():
            self.log_msg("Bank obj not found... Trying again.")
            self.move_camera(90)

        if bank_obj := self.__retry(lambda: self.get_nearest_tag(clr.RED), retry_find_bank):

            def find_bank():
                self.mouse.move_to(bank_obj.random_point())
                return self.mouseover_text(contains="Bank", color=clr.OFF_WHITE)

            if self.__retry(find_bank):
                self.mouse.click()
                return True
            else:
                self.log_msg("Could not find bank.")
                return False
        else:
            return False

    def __exit_bank(self):
        """
        Exits the bank UI in the game.
        """
        close_bank_btn = Rectangle(left=self.win.game_view.left + 485, top=self.win.game_view.top + 10, width=20, height=20)
        self.mouse.move_to(close_bank_btn.random_point())
        self.mouse.click()

    def __begin_crafting(self, item: Item) -> bool:
        self.log_msg(f"Crafting {item}.")

        if craft_btn := self.get_nearest_tag(clr.GREEN):

            def click_craft_btn():
                self.mouse.move_to(craft_btn.random_point())
                return self.mouseover_text(contains=item.name, color=clr.OFF_ORANGE)

            if self.__retry(click_craft_btn):
                self.mouse.click()
                return True
            else:
                self.log_msg(f"Failed to click craft button for {item}.")
                return False
        else:
            self.log_msg(f"Craft button for {item} not found.")
            return False
