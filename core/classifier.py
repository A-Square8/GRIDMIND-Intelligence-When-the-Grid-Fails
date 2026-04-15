import re
 
class UrgencyClassifier:
    def __init__(self):
        
        self.stopwords = {
            "i", "me", "my", "myself", "we", "our", "ours", "ourselves", "you", "your", "yours", 
            "yourself", "yourselves", "he", "him", "his", "himself", "she", "her", "hers", 
            "herself", "it", "its", "itself", "they", "them", "their", "theirs", "themselves", 
            "what", "which", "who", "whom", "this", "that", "these", "those", "am", "is", "are", 
            "was", "were", "be", "been", "being", "have", "has", "had", "having", "do", "does", 
            "did", "doing", "a", "an", "the", "and", "but", "if", "or", "because", "as", "until", 
            "while", "of", "at", "by", "for", "with", "about", "against", "between", "into", 
            "through", "during", "before", "after", "above", "below", "to", "from", "up", "down", 
            "in", "out", "on", "off", "over", "under", "again", "further", "then", "once", "here", 
            "there", "when", "where", "why", "how", "all", "any", "both", "each", "few", "more", 
            "most", "other", "some", "such", "no", "nor", "not", "only", "own", "same", "so", 
            "than", "too", "very", "s", "t", "can", "will", "just", "don", "should", "now", "tell",
            "give", "show", "help", "need", "explain", "describe", "find", "looking", "want", "went", "got"
        }
 
        # high urgency keywords
        self.urgency_high = re.compile(
            r'\b('
            
            # Bleeding & Wounds
            r'bleed|bleeding|hemorrhage|hemorrhaging|gush|gushing|arterial|blood loss|'
            r'laceration|lacerat|deep cut|deep wound|severed|severing|amputation|amputat|'
            r'tourniquet|pressure wound|open wound|exposed bone|open fracture|compound fracture|'
            r'puncture wound|stab|stabbed|stabbing|impaled|impalement|impal|'
            r'gunshot|gunshot wound|gsw|shot|bullet wound|shrapnel|'
            r'eviscerat|evisceration|disembowel|organ exposed|'
 
            # Breathing & Cardiac
            r'not breathing|stopped breathing|no pulse|cardiac arrest|heart attack|'
            r'choking|choke|airway blocked|airway obstruction|suffocating|suffocation|'
            r'drowning|drown|drowned|asphyxiat|asphyxia|respiratory arrest|'
            r'anaphylaxis|anaphylactic|allergic shock|throat closing|'
            r'chest pain|crushing chest|chest pressure|left arm pain|jaw pain|'
            r'stroke|facial droop|arm weakness|speech slurred|sudden numbness|'
            r'cardiac|defibrillate|cpr|resuscitat|'
 
            # Unconscious & Neurological
            r'unconscious|unresponsive|passed out|not waking|collapsed|'
            r'seizure|seizing|convulsion|convulsing|fitting|fits|'
            r'concussion|head trauma|skull fracture|brain bleed|intracranial|'
            r'coma|comatose|unaware|eyes rolled|'
 
            # Poisoning & Toxic
            r'poison|poisoned|poisoning|toxic|toxin|venom|envenomation|'
            r'snakebite|snake bite|spider bite|scorpion sting|jellyfish sting|'
            r'overdose|overdosed|drug overdose|carbon monoxide|co poisoning|'
            r'chemical exposure|acid burn|alkali burn|corrosive|'
            r'mushroom poison|plant poison|berries poison|toxic ingestion|'
 
            # Burns & Temperature Extremes
            r'burn|burning|burned|severe burn|third degree|full thickness burn|'
            r'chemical burn|electrical burn|flash burn|fire burn|'
            r'hypothermia|hypothermic|core temp drop|frozen|freezing to death|'
            r'frostbite severe|heatstroke|heat stroke|hyperthermia|'
            r'core temperature|dangerously cold|body temp dropping|'
 
            # Trauma & Injury
            r'broken bone|fracture|fractured|crushed|crush injury|'
            r'spinal injury|neck injury|back broken|paralyzed|cant move legs|'
            r'internal bleeding|internal injury|abdominal trauma|blunt trauma|'
            r'head injury|skull crack|jaw broken|'
            r'eye injury|eye puncture|vision lost|blinded|'
 
            # Infection & Sepsis
            r'sepsis|septic|blood poisoning|systemic infection|'
            r'gangrene|necrosis|necrotizing|flesh eating|black tissue|'
            r'infected wound critical|red streaks|spreading redness|'
            r'high fever wound|fever above 40|fever above 104|'
            r'pus spreading|wound smell|rotting flesh|'
 
            # Childbirth Emergency
            r'giving birth|labor now|delivering baby|baby coming|crowning|'
            r'umbilical|placenta|stillbirth|breech birth|premature birth|'
            r'postpartum hemorrhage|eclampsia|'
 
            # Drowning & Suffocation
            r'drowning|drown|near drowning|water in lungs|inhaled water|'
            r'buried alive|trapped under|airway crushed|neck compressed|'
            r'hanged|hanging|strangulation|strangulat|'
 
            # Mental Health Emergency
            r'suicide|suicidal|killing myself|end my life|want to die now|'
            r'self harm severe|cutting deep|overdose attempt|'
 
            # Structural & Environmental Emergency
            r'building collapse|roof collapse|buried under rubble|'
            r'trapped in fire|fire spreading|can t escape fire|'
            r'swept away|flash flood now|rising water fast|'
            r'avalanche buried|snow buried|'
            r'electrocuted|electrocution|electric shock|live wire contact'
            r')\b', re.IGNORECASE
        )
 
        # medium urgency keywords
        self.urgency_medium = re.compile(
            r'\b('
 
            # General Illness
            r'sick|illness|ill|fever|high temp|temperature|chills|shivering|'
            r'vomiting|vomit|nausea|nauseous|diarrhea|diarrhoea|stomach pain|'
            r'abdominal pain|cramps|stomach cramp|bowel|constipation|'
            r'headache|migraine|head pain|pressure in head|'
            r'dizziness|dizzy|lightheaded|vertigo|fainting|faint|'
            r'dehydration|dehydrat|thirsty|dry mouth|dark urine|'
 
            # Wounds & Minor Injuries
            r'infected|infection|wound infected|pus|discharge|'
            r'sprain|sprained|twisted|swollen|swelling|inflammation|'
            r'blister|blistered|rash|skin rash|hives|itching severe|'
            r'frostbite|mild frostbite|numb fingers|numb toes|'
            r'minor burn|first degree burn|sunburn severe|'
            r'bruise|bruising|contusion|hematoma|'
            r'pain|painful|aching|soreness|throbbing|'
 
            # Hunger & Nutrition
            r'starving|starvation|hungry|no food|haven t eaten|'
            r'malnutrition|malnourished|weak from hunger|'
            r'vitamin deficiency|scurvy|rickets|pellagra|'
            r'muscle weakness|extreme fatigue|'
 
            # Mental & Cognitive
            r'hallucinating|hallucination|delirious|delirium|confused|confusion|'
            r'disoriented|cant think|brain fog|'
            r'panic attack|anxiety severe|hyperventilating|'
            r'exhaustion|exhausted|sleep deprived|no sleep|'
 
            # Environmental Stress
            r'lost|stranded|separated|alone in wilderness|'
            r'exposure|exposed|wet and cold|soaked|'
            r'altitude sickness|mountain sickness|'
            r'animal attack|bitten by animal|scratched by animal|'
 
            # Dental & Pain
            r'tooth pain|toothache|dental infection|abscess|'
            r'eye infection|conjunctivitis|pink eye|'
            r'ear infection|ear pain|'
            r'urinary infection|uti|burning urination|'
 
            # Pregnancy & Childbirth
            r'pregnant|pregnancy|labor|contractions|'
            r'miscarriage|bleeding pregnant|'
 
            # Resource Crisis
            r'running out of water|last water|'
            r'running out of food|last food|'
            r'shelter failing|shelter destroyed|'
            r'fire going out|losing fire|no heat|'
            r'medicine running out|last dose'
            r')\b', re.IGNORECASE
        )
 
        # domain specefic keyword
        self.mode_survival = re.compile(
            r'\b('
 
            # --- GLOBAL COLLAPSE SCENARIOS ---
            r'apocalypse|apocalyptic|post apocalypse|post-apocalyptic|'
            r'collapse|societal collapse|grid down|grid collapse|grid failure|'
            r'shtf|wrol|teotwawki|ww3|world war 3|world war three|'
            r'nuclear|nuclear war|nuclear fallout|nuclear blast|nuclear winter|'
            r'radiation|radioactive|fallout shelter|rad exposure|'
            r'emp|electromagnetic pulse|emp attack|emp strike|'
            r'solar flare|coronal mass ejection|cme|geomagnetic storm|'
            r'zombie|zombie apocalypse|undead|infected horde|'
            r'pandemic|plague|mass disease|bioweapon|biological attack|'
            r'quarantine|lockdown permanent|martial law|'
            r'invasion|occupation|enemy forces|civil war|urban warfare|'
            r'end of world|end times|doomsday|armageddon|'
            r'infrastructure collapse|power grid destroyed|water system down|'
            r'supply chain collapse|food system collapse|'
            r'currency collapse|economic collapse|famine|mass starvation|'
 
            # --- WILDERNESS & ENVIRONMENT ---
            r'wilderness|wild|backcountry|remote|off-grid|offgrid|off grid|'
            r'jungle|rainforest|dense forest|deep woods|forest survival|'
            r'desert|arid|no water desert|extreme heat survival|'
            r'arctic|tundra|polar|extreme cold|subzero|'
            r'mountain|high altitude|alpine|above treeline|'
            r'swamp|wetland|marsh|bog|'
            r'island|stranded island|shipwreck|castaway|'
            r'cave|underground|spelunking emergency|'
            r'lost in the woods|lost in forest|lost in desert|lost in mountains|'
            r'stranded|abandoned|isolated|no civilization|'
 
            # --- NATURAL DISASTERS ---
            r'hurricane|typhoon|cyclone|'
            r'tornado|twister|funnel cloud|'
            r'earthquake|aftershock|seismic|'
            r'tsunami|tidal wave|mega wave|'
            r'flood|flash flood|rising water|river flood|'
            r'wildfire|forest fire|brush fire|firestorm|'
            r'blizzard|snowstorm|whiteout|ice storm|'
            r'avalanche|landslide|mudslide|rockslide|'
            r'volcanic|volcano|ash fall|lava|pyroclastic|'
            r'drought|extreme drought|no rain months|'
            r'dust storm|sandstorm|haboob|'
 
            # --- DOMAIN 03: WATER ---
            r'purify water|water purification|water filtration|filter water|'
            r'boil water|water treatment|make water safe|'
            r'stagnant water|murky water|dirty water|contaminated water|'
            r'river water|stream water|lake water|pond water|'
            r'rainwater|rain catchment|collect rain|dew collection|'
            r'solar still|improvised filter|charcoal filter|sand filter|'
            r'water source|find water|no water|water shortage|'
            r'well|digging well|water table|groundwater|spring water|'
            r'distill water|distillation|evaporation still|'
            r'water storage|water container|water barrel|'
            r'iodine tablets|purification tablets|bleach water|'
            r'giardia|cryptosporidium|waterborne illness|water parasite|'
 
            # --- DOMAIN 04: FOOD FORAGING & HUNTING ---
            r'forage|foraging|wild edible|edible plant|wild food|'
            r'mushroom|fungi|wild mushroom|identify mushroom|'
            r'berry|wild berry|edible berry|poisonous berry|'
            r'root|tuber|wild root|edible root|bulb|'
            r'bark|edible bark|cambium|pine needle|'
            r'insect|insects|bug eating|entomophagy|grub|larvae|worm|'
            r'hunt|hunting|game|wild game|deer|rabbit|squirrel|'
            r'trap|trapping|snare|deadfall trap|pit trap|'
            r'fish|fishing|improvised fishing|fish trap|'
            r'spearfishing|improvised spear|fish weir|'
            r'preserve food|food preservation|smoking meat|drying meat|'
            r'jerky|salt cure|ferment|fermentation|pickling|'
            r'rendering fat|animal fat|tallow|lard|'
            r'bone broth|marrow|organ meat|offal|'
            r'caloric intake survival|starvation ration|'
 
            # --- DOMAIN 05: AGRICULTURE & SEEDS ---
            r'seed saving|save seeds|seed bank|seed storage|'
            r'grow food|growing food|plant food|vegetable garden|'
            r'crop|crops|harvest|planting|sowing|'
            r'soil|composting|compost|fertilizer|manure|'
            r'crop rotation|companion planting|intercropping|'
            r'irrigation|water crops|drip irrigation|'
            r'pest control|natural pesticide|insect repellent garden|'
            r'greenhouse|cold frame|season extension|'
            r'root cellar|food storage|vegetable storage|'
            r'grain|wheat|corn|maize|potato|sweet potato|'
            r'legume|bean|lentil|pea|protein crop|'
            r'fruit tree|orchard|grafting|propagation|cutting|'
            r'animal husbandry|goat|chicken|rabbit|livestock|'
            r'beekeeping|bees|honey|wax|'
 
            # --- DOMAIN 06: FIRE & THERMAL ---
            r'start fire|start a fire|fire starting|make fire|make a fire|ignite|ignition|'
            r'flint|flint and steel|ferro rod|fire starter|'
            r'friction fire|bow drill|hand drill|fire plow|'
            r'tinder|kindling|fire bundle|char cloth|'
            r'fire wood|firewood|fuel wood|gather wood|'
            r'fire pit|hearth|fire ring|fire shelter|'
            r'cooking fire|open fire cooking|campfire cooking|'
            r'improvised stove|rocket stove|tin can stove|clay stove|'
            r'thermal mass|heat retention|stone cooking|'
            r'warmth|keeping warm|insulate body|body heat|'
            r'hypothermia prevention|stay warm|'
            r'solar heat|passive solar|solar cooker|'
            r'fire safety|fire control|contain fire|'
            r'charcoal|make charcoal|biochar|'
            r'signal fire|rescue fire|signal smoke|'
 
            # --- DOMAIN 07: SHELTER ---
            r'build shelter|shelter construction|improvised shelter|'
            r'lean-to|debris hut|a-frame|tarp shelter|'
            r'dig shelter|underground shelter|earth shelter|bunker|'
            r'insulation|thermal insulation|wall insulation|floor insulation|'
            r'waterproof|waterproofing|weatherproof|rain shelter|'
            r'log cabin|timber frame|post and beam|'
            r'mud brick|adobe|cob|clay building|'
            r'thatch|thatching|roof grass|leaf roof|'
            r'stone wall|dry stone|rock shelter|cave shelter|'
            r'ventilation|air circulation|shelter airflow|'
            r'shelter location|site selection|high ground|flood safe|'
            r'camouflage shelter|hidden camp|concealed position|'
            r'emergency bivouac|bivvy|snow shelter|snow cave|quinzee|'
 
            # --- DOMAIN 08: WEAPONS & SELF-DEFENSE ---
            r'improvised weapon|makeshift weapon|craft weapon|'
            r'bow|bow and arrow|archery|arrow|fletching|bowstring|'
            r'slingshot|catapult|atlatl|throwing weapon|'
            r'spear|improvised spear|sharpened stick|'
            r'knife|blade|improvised blade|knapping|flint knife|'
            r'club|bludgeon|mace|flail|improvised club|'
            r'crossbow|improvised crossbow|bolt|'
            r'defense|self defense|protect camp|perimeter|'
            r'ambush|escape|evade|evasion|'
            r'fortify|fortification|barricade|reinforced door|'
            r'tripwire|alarm system|perimeter alarm|'
            r'group defense|watch|guard duty|patrol|'
            r'camouflage|ghillie|concealment|hide position|'
            r'firearm|gun|ammunition|reload|jam|clean gun|'
            r'gunpowder|black powder|improvised ammunition|'
 
            # --- DOMAIN 09: NAVIGATION ---
            r'navigate|navigation|find direction|'
            r'no gps|without gps|gps down|lost direction|'
            r'compass|magnetic compass|improvised compass|'
            r'dead reckoning|pace count|bearing|azimuth|'
            r'celestial navigation|star navigation|north star|polaris|'
            r'sun navigation|shadow stick|solar direction|'
            r'map reading|topographic map|topo map|contour lines|'
            r'terrain reading|landform|ridge|valley|saddle|'
            r'landmark|natural landmark|triangulate|'
            r'track|tracking|animal track|human track|sign tracking|'
            r'trail|trail marking|blaze trail|cairn|'
            r'river navigation|follow river|downstream|'
            r'night navigation|moon navigation|'
            r'scouting|reconnaissance|recon|area assessment|'
 
            # --- DOMAIN 10: BASIC ELECTRONICS & REPAIR ---
            r'electronics|electronic repair|circuit|'
            r'salvage parts|salvaging electronics|scrap electronics|'
            r'battery|battery repair|dead battery|charge battery|'
            r'solar panel|solar power|photovoltaic|pv panel|'
            r'wind power|improvised generator|hand crank|'
            r'wiring|wire|connect wire|splice wire|'
            r'multimeter|test circuit|continuity|'
            r'led|light|improvised light|oil lamp|'
            r'radio|transistor radio|am fm radio|shortwave|'
            r'capacitor|resistor|diode|transistor|'
            r'charge|charging|power bank|12 volt|'
            r'motor|electric motor|salvage motor|'
            r'inverter|voltage regulator|step down|'
            r'fuse|short circuit|electrical safety|'
            r'antenna|antenna build|signal boost|'
 
            # --- DOMAIN 11: RADIO & COMMUNICATION ---
            r'ham radio|amateur radio|transceiver|handheld radio|'
            r'morse code|cw|dit dah|key|'
            r'antenna|dipole|vertical antenna|wire antenna|'
            r'frequency|channel|bandwidth|propagation|'
            r'signal|radio signal|signal strength|'
            r'two way radio|walkie talkie|frs|gmrs|'
            r'shortwave|hf radio|vhf|uhf|'
            r'repeater|relay|radio relay|'
            r'signal mirror|heliograph|visual signal|'
            r'smoke signal|signal fire|ground signal|'
            r'flag signal|semaphore|hand signal|'
            r'encryption|coded message|cipher|'
            r'radio silence|opsec|communication security|'
 
            # --- DOMAIN 12: TRAUMA & FIELD SURGERY ---
            r'field surgery|improvised surgery|'
            r'suture|suturing|stitch wound|close wound|'
            r'wound care|wound cleaning|irrigate wound|'
            r'antiseptic|disinfect|clean cut|sterilize|'
            r'splint|improvised splint|bone splint|'
            r'traction|realign bone|set bone|'
            r'triage|mass casualty|priority wound|'
            r'airway|airway management|jaw thrust|chin lift|'
            r'chest seal|pneumothorax|tension pneumo|'
            r'hemostatic|packing wound|gauze|'
            r'pain management|improvised analgesic|natural painkiller|'
            r'anesthesia|improvised anesthesia|numbing|'
            r'amputation field|field amputation|'
            r'dental extraction|pull tooth|'
            r'childbirth assist|deliver baby|'
            r'bone saw|scalpel|improvised scalpel|'
            r'cauterize|cauterization|burn wound closed|'
 
            # --- DOMAIN 13: METALWORKING & TOOLMAKING ---
            r'blacksmith|blacksmithing|forge|forging|'
            r'smelt|smelting|melt metal|cast metal|'
            r'anvil|hammer|tongs|bellows|'
            r'scrap metal|salvage metal|metal work|'
            r'sharpen|sharpening|hone|whetstone|'
            r'knife making|blade smithing|tool making|'
            r'weld|welding|arc weld|gas weld|'
            r'casting|mold|pour metal|'
            r'hardening|tempering|quench|anneal|'
            r'ore|iron ore|smelt iron|'
            r'charcoal forge|coal forge|'
            r'copper|bronze|brass|alloy|'
            r'wire drawing|sheet metal|roll metal|'
            r'nail|screw|bolt|improvised fastener|'
            r'repair tool|fix tool|'
 
            # --- DOMAIN 14: TEXTILES & HANDCRAFT ---
            r'sew|sewing|stitch|needle thread|'
            r'leather|leatherwork|tan leather|tanning|'
            r'plant fiber|natural fiber|hemp|flax|nettle fiber|'
            r'spin|spinning|spindle|yarn|thread|'
            r'weave|weaving|loom|fabric|cloth|'
            r'knit|knitting|crochet|'
            r'waterproof fabric|wax cloth|oilskin|'
            r'patch|repair clothing|darn|'
            r'hide|animal hide|rawhide|buckskin|'
            r'felting|wool felt|compress wool|'
            r'cordage|rope|make rope|braid cord|twine|'
            r'knot|knot tying|lashing|binding|'
            r'basket|weave basket|container craft|'
            r'pottery|clay pot|ceramic|fire clay|'
 
            # --- DOMAIN 15: MENTAL HEALTH & GROUP DYNAMICS ---
            r'morale|group morale|team morale|'
            r'conflict|group conflict|interpersonal|'
            r'leadership|survival leader|'
            r'stress|trauma|ptsd|survivor guilt|'
            r'decision making|under pressure|'
            r'ration|rationing|fair share|divide resources|'
            r'group size|community|tribe|'
            r'trust|distrust|stranger|threat assessment|'
            r'mental breakdown|psychological|'
            r'isolation|loneliness|alone long term|'
            r'children survival|kids in collapse|'
            r'elderly survival|disabled survival|'
            r'grief|death in group|loss|'
            r'hope|motivation|purpose|will to survive'
            r')\b', re.IGNORECASE
        )
 
        # limited resource keywords
        self.resources_limited = re.compile(
            r'\b('
            r'nothing|have nothing|starting from nothing|'
            r'only have|all i have|only thing i have|'
            r'no tools|without tools|bare hands|'
            r'no medicine|no medical supplies|no drugs|no antibiotics|'
            r'no food|no water|no shelter|no gear|no equipment|'
            r'scavenge|scavenging|scrap|scrounging|'
            r'improvise|improvised|makeshift|'
            r'limited|very limited|extremely limited|'
            r'trapped|stuck with|can t get|'
            r'out of|ran out|depleted|exhausted supply|used last|'
            r'destroyed|lost my|stolen|'
            r'empty|empty handed|'
            r'alone|by myself|solo|no group|just me|'
            r'absolutely no|zero resources|'
            r'found|only found|scavenged|picked up|'
            r'broken|damaged|partial|half|'
            r'primitive|stone age|from scratch|'
            r'no electricity|no power|no fuel|'
            r'no fire|cant make fire|lost fire|'
            r'no clean water|no potable|'
            r'single item|one item|only item|'
            r'wilderness only|nature only|forest only|'
            r'no money|no trade|no barter|'
            r'without|without any|lacking|missing|'
            r'minimal|bare minimum|stripped down'
            r')\b', re.IGNORECASE
        )
 
        # moderate resource keywords
        self.resources_moderate = re.compile(
            r'\b('
            r'some|a few|limited supply|small supply|'
            r'kit|basic kit|starter kit|survival kit|'
            r'bag|backpack|pack|rucksack|'
            r'bug out bag|bob|go bag|72 hour bag|'
            r'supplies|some supplies|partial supplies|'
            r'stash|cache|cached|stored|'
            r'basic tools|hand tools|simple tools|'
            r'first aid kit|basic first aid|'
            r'small group|two people|three people|family|'
            r'one vehicle|truck|van|car|'
            r'partial power|solar|battery bank|generator|'
            r'small farm|garden|chickens|goats|'
            r'some medicine|partial medicine|basic meds|'
            r'knife|multitool|axe|hatchet|'
            r'rope|cord|paracord|tarp|'
            r'radio|walkie talkie|handheld|'
            r'moderate|enough for now|for a while|short term'
            r')\b', re.IGNORECASE
        )
 
    def classify(self, query: str) -> dict:
        urgency = "LOW"
        mode = "NORMAL"
        resources = "FULL"
 
        if self.urgency_high.search(query):
            urgency = "HIGH"
        elif self.urgency_medium.search(query):
            urgency = "MEDIUM"
 
        if self.mode_survival.search(query):
            mode = "SURVIVAL"
 
        if self.resources_limited.search(query):
            resources = "LIMITED"
        elif self.resources_moderate.search(query):
            resources = "MODERATE"
 
        return {
            "mode": mode,
            "resources": resources,
            "urgency": urgency
        }
        
    def extract_search_queries(self, query: str) -> list[str]:
        """
        Decomposes a conversational prompt into dense semantic queries by filtering out
        filler words and punctuation, improving vector similarity bounds.
        """
        clauses = re.split(r'[.,;?!]', query)
        search_queries = []
        for clause in clauses:
            words = clause.lower().split()
            dense_words = [w for w in words if w not in self.stopwords and len(w) > 2]
            if len(dense_words) >= 2:
                search_queries.append(" ".join(dense_words))
                
        return search_queries if search_queries else [query]
 
    def format_for_prompt(self, classification: dict) -> str:
        return (
            f"mode: {classification['mode']}\n"
            f"resources: {classification['resources']}\n"
            f"urgency: {classification['urgency']}"
        )
 