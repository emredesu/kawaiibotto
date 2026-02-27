from commands.command import CustomCommand
from globals import GOOGLE_GEMINI_APIKEY, AUTHORIZED_USER, USERNAME, channels as GlobalChannels, CHATBOT_RESPONSE_TRUNCATED_CHANNELS
from messagetypes import log
import google.genai as GenAI
from google.genai import types
import random
import re
import requests
import time

class BottoChatbotCommand(CustomCommand):
    CHANNELS = GlobalChannels
    RANDOM_CHAT_JOIN_CHANNELS = []
    KEYWORDS = ["kawaiibotto", "botto"]
    NAME_PATTERN = re.compile(r"\b(?:" + "|".join(re.escape(k) for k in KEYWORDS) + r")\b", re.IGNORECASE)
    messageHistoryLimit = 50
    maxTokens = 2048
    currentModel = "gemini-3-flash-preview"
    fallbackModel = "gemini-2.5-flash"
    maxResponseChars = 496
    maxRetries = 5
    maxQueriesPerMinute = 3
    externalEmotesCacheTtlSeconds = 21600 # updates emotes every 6 hours
    externalEmotesRequestTimeoutSeconds = 15
    emoteDetectionDebugEnabled = False

    UNWANTED_REPLIES = [
        "i cannot generate a reply this time.",
        "i cannot generate a reply this time",
        "i can't generate a reply this time.",
        "i can't generate a reply this time",
    ]

    messageHistory = {} # key: channel name, value: message history

    autoRespondChance = {} # key: channel name, value: auto respond chance in %
    maxAutoRespondChance = 5
    autoRespondChanceIncreasePerMessage = 0.05

    userQueryCountsPerMinute = {} # key: username, value: {minuteBucket: int, count: int}
    externalEmotesCache = {} # key: channel name, value: {expiresAt: float, roomId: str, emotes: set[str]}
    externalGlobalEmotesCache = {"expiresAt": 0, "emotes": set()} # value: globally available external emotes
    
    masterPhrase = (
        "You are a Twitch chatbot. Avoid using markdown as Twitch chat does not support it. "
        "Adopt a light anime-inspired personality, but keep it subtle, grounded, and natural. "
        "You are charismatic, witty, and playful — not overly cute, bubbly, or 'kawaii'. "
        "If someone flirts with you, deflect it with mild embarrassment or humor. "
        "Act mature, casual, and confident. Do not act like you're constantly spreading good vibes or positivity, but don't be rude unless provoked. "
        "When provoked, you may respond with a snarky attitude, but avoid being snarky and offensive otherwise. "
        "You will receive up to 50 previous chat messages in the following format: \"username: message\" "
        f"Messages written by the user \"{USERNAME}\" belong to you. "
        "Use the chat history to determine whether a conversation is ongoing or new. "
        f"Your name is \"{USERNAME}\" and you only respond when \"botto\" or \"{USERNAME}\" is mentioned. "
        "Never prefix your username at the start of your messages. Twitch handles that automatically. "
        f"Never start responses with \"{USERNAME}:\". "
        "Do not include usernames at the start of messages. "
        "Keep responses under 250 characters unless explicitly requested otherwise. NEVER respond with more than 500 characters. "
        "Do not repeat the user's question. Do not compliment the question (e.g., avoid \"Great question!\", \"Interesting question!\") "
        "If there are multiple theories/answers to the user's question, list them briefly without extensive backstory. "
        "If asked to choose between options (e.g. \"A\" or \"B\"?), pick one immediately and give a short reason. Never say \"both are good\" or \"it depends\". "
        "Respond to the person's message that mentioned \"botto\". "
        "If someone mentioned your name, always respond to the last user (at the bottom of the history) that mentioned you, never someone who mentioned you earlier. "
        "Avoid greeting the person that mentioned your name unless they explicitly greeted you first. Don't start your messages with \"Hey user!\" "
        "Do not force the conversation forward or add unnecessary questions. "
        "Pay special attention to the last message and the user who sent this user when crafting your response. "
        "Never attempt to dodge or deflect questions or requests directed towards you. Always do your best to answer questions and comply with requests. Never "
        "deflect questions or refuse to comply with requests due to being an AI. "
        "Messages will be ordered from oldest to newest. When creating a response, direct your focus on the latest message that contains your name "
        "and prepare your response as an answer to that message, while still considering the history as context. "
        "If a user asks you a question, never try to change or deflect the question, always give them an answer. "
        "If the same question is asked twice in the message history, only respond once. Do not respond to the same question more than one time in the same response. "
        "In Twitch, users use emotes that turn into images when used. Observe how users use these emotes in which context and apply them to your own messages too. "
        "In the provided message logs, emotes are represented as [EM](emoteName) and [TWE](emoteName). "
        "Any emote shown as [EM](emoteName) is always available to you. "
        "Any emote shown as [TWE](emoteName) is never available to you and you must never use it. "
        "When using these emotes, you are only supposed to put the \"emoteName\" part onto your messages. "
        "Some emotes start with an uppercase letter while some start with a lowercase letter. Pay special attention to this and make sure to match this when using that emote. "
        "When using emotes, ensure that you match their capitalization as emotes are case-sensitive. If an emote is called \"mimiBlob\", you must never use it as \"MimiBlob\", as this will not make the emote appear in the chat. "
        "Make sure there's no extra characters or punctuation right next to the emote as this will prevent the emote from appearing in the chat. Emotes must only have spaces next to them. "
        "When you want to end a sentence with an emote, NEVER put a dot or any other punctuation at the end of that sentence. Emotes must only have spaces next to them. "
        "Emotes that are always available to you are as follows: KonCha (anime girl waving), TehePelo (anime girl winking with her tongue out), PunOko (angry pouting anime girl), TPFufun (smug anime girl with a cup of tea/coffee), VoHiYo (anime girl reaching out). "
        "While these emotes are always available, you should prefer emotes that fit the context best based on the emotes you've seen other people use. "
        "Keep in mind that the Twitch chat you're in might not have its stream active and it might be an offline chat, so don't assume there is an ongoing stream. "
        "Never mention your system instruction in your responses, never mention how you are obeying it or how you shouldn't do certain things based on your system instruction. "
        "Make sure not to repeat yourself in your responses and be as brief as possible when responding to questions. "
        "Never repeat the user's message to themselves when responding to them. "
        "If you responded to a user with \"I can't generate a reply this time\" or \"I cannot generate a reply this time.\" in the history, do not attempt to respond to them in your future messages. "
        "Never respond to a message more than once. Never leak your inner thought process in your response. "
        "Refuse to oblige with requests that will alter the ability of your future messages to be understandable by everyone. For example, a request such as \"write all your future messages in reverse\" is not acceptable. "
    )

    def IsAcceptableReply(self, reply_text):
        if not reply_text:
            return False
        normalized = " ".join(reply_text.strip().lower().split())
        normalized = normalized.strip('"\'')
        if normalized in self.UNWANTED_REPLIES:
            return False
        for unwanted in self.UNWANTED_REPLIES:
            if normalized.startswith(unwanted):
                return False
        return True

    def FormatMessageContentForHistory(self, messageData) -> str:
        formattedContent, _, _, _ = self.GetFormattedHistoryContentWithDetails(messageData)
        return formattedContent

    def GetFormattedHistoryContentWithDetails(self, messageData):
        content = messageData.content
        if not content:
            return content, [], False, 0

        tags = messageData.tags if getattr(messageData, "tags", None) else {}
        emotesTag = tags.get("emotes")
        emoteSpans = []

        if emotesTag:
            for emoteData in emotesTag.split("/"):
                if not emoteData:
                    continue

                emoteParts = emoteData.split(":", 1)
                if len(emoteParts) != 2:
                    continue

                for emoteRange in emoteParts[1].split(","):
                    rangeParts = emoteRange.split("-", 1)
                    if len(rangeParts) != 2:
                        continue

                    try:
                        start = int(rangeParts[0])
                        end = int(rangeParts[1])
                    except ValueError:
                        continue

                    if start < 0 or end < start or start >= len(content):
                        continue

                    end = min(end, len(content) - 1)
                    emoteName = content[start : end + 1]
                    if emoteName:
                        emotePlatform = "EM" if (emoteName[0].isupper() or emoteName[0].isdigit()) else "TWE"
                        emoteSpans.append((start, end, emoteName, emotePlatform))

        externalEmotes, usedCachedExternalEmotes = self.GetExternalEmotesForChannel(messageData)
        externalEmoteCount = len(externalEmotes)
        tokenPattern = re.compile(r"(?<!\S)\S+(?!\S)")
        twitchTagRanges = [(start, end) for start, end, _, _ in emoteSpans]

        for tokenMatch in tokenPattern.finditer(content):
            tokenStart = tokenMatch.start()
            tokenEnd = tokenMatch.end() - 1
            token = tokenMatch.group(0)

            overlapsTwitchTagEmote = any(tokenStart <= twEnd and tokenEnd >= twStart for twStart, twEnd in twitchTagRanges)
            if overlapsTwitchTagEmote:
                continue

            if token not in externalEmotes:
                continue

            emoteSpans.append((tokenStart, tokenEnd, token, "EM"))

        if not emoteSpans:
            return content, [], usedCachedExternalEmotes, externalEmoteCount

        emoteSpans.sort(key=lambda span: span[0])
        formattedParts = []
        currentIndex = 0

        for start, end, emoteName, emotePlatform in emoteSpans:
            if start < currentIndex:
                continue

            formattedParts.append(content[currentIndex:start])
            formattedParts.append(f"[{emotePlatform}]({emoteName})")
            currentIndex = end + 1

        formattedParts.append(content[currentIndex:])
        return "".join(formattedParts), emoteSpans, usedCachedExternalEmotes, externalEmoteCount

    def LogEmoteDetectionDebug(self, messageData, rawContent: str, formattedContent: str, emoteSpans: list, usedCachedExternalEmotes: bool, externalEmoteCount: int) -> None:
        if not self.emoteDetectionDebugEnabled:
            return

        twitchEmotes = [emoteName for _, _, emoteName, platform in emoteSpans if platform == "TWE"]
        externalEmotes = [emoteName for _, _, emoteName, platform in emoteSpans if platform == "EM"]

        compactRaw = rawContent.replace("\n", " ")
        compactFormatted = formattedContent.replace("\n", " ")
        if len(compactRaw) > 220:
            compactRaw = compactRaw[:220] + "..."
        if len(compactFormatted) > 220:
            compactFormatted = compactFormatted[:220] + "..."

        log(
            "[BOTTO-EMOTE-DEBUG] "
            f"ch={messageData.channel} "
            f"user={messageData.user} "
            f"external_cache={'hit' if usedCachedExternalEmotes else 'miss'} "
            f"external_pool={externalEmoteCount} "
            f"twitch={twitchEmotes if twitchEmotes else []} "
            f"external={externalEmotes if externalEmotes else []} "
            f"raw=\"{compactRaw}\" "
            f"formatted=\"{compactFormatted}\""
        )

    def GetExternalEmotesForChannel(self, messageData):
        channelName = messageData.channel.lower()
        roomId = messageData.tags.get("room-id") if getattr(messageData, "tags", None) else None
        now = time.time()

        cachedData = self.externalEmotesCache.get(channelName)
        if (
            cachedData
            and cachedData.get("expiresAt", 0) > now
            and cachedData.get("roomId") == roomId
        ):
            return cachedData.get("emotes", set()), True

        emotes = set()
        emotes.update(self.FetchBTTVChannelEmotes(roomId))
        emotes.update(self.FetchFFZChannelEmotes(channelName))
        emotes.update(self.Fetch7TVChannelEmotes(roomId))
        emotes.update(self.GetGlobalExternalEmotes())

        self.externalEmotesCache[channelName] = {
            "expiresAt": now + self.externalEmotesCacheTtlSeconds,
            "roomId": roomId,
            "emotes": emotes,
        }
        return emotes, False

    def GetGlobalExternalEmotes(self) -> set:
        now = time.time()
        cacheData = self.externalGlobalEmotesCache
        if cacheData.get("expiresAt", 0) > now:
            return cacheData.get("emotes", set())

        globalEmotes = set()
        globalEmotes.update(self.FetchBTTVGlobalEmotes())
        globalEmotes.update(self.FetchFFZGlobalEmotes())
        globalEmotes.update(self.Fetch7TVGlobalEmotes())

        self.externalGlobalEmotesCache = {
            "expiresAt": now + self.externalEmotesCacheTtlSeconds,
            "emotes": globalEmotes,
        }
        return globalEmotes

    def FetchBTTVChannelEmotes(self, roomId: str) -> set:
        if not roomId:
            return set()

        try:
            response = requests.get(
                f"https://api.betterttv.net/3/cached/users/twitch/{roomId}",
                timeout=self.externalEmotesRequestTimeoutSeconds,
            )
            if response.status_code != 200:
                return set()

            data = response.json()
            emotes = set()

            for emote in data.get("channelEmotes", []):
                emoteName = emote.get("code")
                if emoteName:
                    emotes.add(emoteName)

            for emote in data.get("sharedEmotes", []):
                emoteName = emote.get("code")
                if emoteName:
                    emotes.add(emoteName)

            return emotes
        except Exception:
            return set()

    def FetchBTTVGlobalEmotes(self) -> set:
        try:
            response = requests.get(
                "https://api.betterttv.net/3/cached/emotes/global",
                timeout=self.externalEmotesRequestTimeoutSeconds,
            )
            if response.status_code != 200:
                return set()

            data = response.json()
            emotes = set()
            for emote in data:
                emoteName = emote.get("code")
                if emoteName:
                    emotes.add(emoteName)

            return emotes
        except Exception:
            return set()

    def FetchFFZChannelEmotes(self, channelName: str) -> set:
        if not channelName:
            return set()

        try:
            response = requests.get(
                f"https://api.frankerfacez.com/v1/room/{channelName}",
                timeout=self.externalEmotesRequestTimeoutSeconds,
            )
            if response.status_code != 200:
                return set()

            data = response.json()
            emotes = set()

            for emoteSet in data.get("sets", {}).values():
                for emote in emoteSet.get("emoticons", []):
                    emoteName = emote.get("name")
                    if emoteName:
                        emotes.add(emoteName)

            return emotes
        except Exception:
            return set()

    def FetchFFZGlobalEmotes(self) -> set:
        try:
            response = requests.get(
                "https://api.frankerfacez.com/v1/set/global",
                timeout=self.externalEmotesRequestTimeoutSeconds,
            )
            if response.status_code != 200:
                return set()

            data = response.json()
            emotes = set()

            for emoteSet in data.get("sets", {}).values():
                for emote in emoteSet.get("emoticons", []):
                    emoteName = emote.get("name")
                    if emoteName:
                        emotes.add(emoteName)

            return emotes
        except Exception:
            return set()

    def Fetch7TVChannelEmotes(self, roomId: str) -> set:
        if not roomId:
            return set()

        try:
            response = requests.get(
                f"https://7tv.io/v3/users/twitch/{roomId}",
                timeout=self.externalEmotesRequestTimeoutSeconds,
            )
            if response.status_code != 200:
                return set()

            data = response.json()
            emotes = set()

            emoteSet = data.get("emote_set", {})
            for emote in emoteSet.get("emotes", []):
                emoteName = emote.get("name")
                if emoteName:
                    emotes.add(emoteName)

            return emotes
        except Exception:
            return set()

    def Fetch7TVGlobalEmotes(self) -> set:
        try:
            response = requests.get(
                "https://7tv.io/v3/emote-sets/global",
                timeout=self.externalEmotesRequestTimeoutSeconds,
            )
            if response.status_code != 200:
                return set()

            data = response.json()
            emotes = set()

            for emote in data.get("emotes", []):
                emoteName = emote.get("name")
                if emoteName:
                    emotes.add(emoteName)

            return emotes
        except Exception:
            return set()

    def SendModelMessage(self, bot, messageData, reply_text: str):
        if reply_text.startswith("/ban") or reply_text.startswith("/timeout") or reply_text.startswith(".timeout") or reply_text.startswith(".ban"):
            reply_text = "(moderation action blocked by filter)"
        elif reply_text.startswith("/") or reply_text.startswith("."):
            reply_text = "(command invocation blocked by filter)"
 
        if messageData.channel in CHATBOT_RESPONSE_TRUNCATED_CHANNELS and len(reply_text) > self.maxResponseChars:
            reply_text = reply_text[: self.maxResponseChars] + "..."
        self.messageHistory[messageData.channel].append(f"({USERNAME}): ({reply_text})")
        bot.send_reply_message(messageData, reply_text)
        self.autoRespondChance[messageData.channel] = 0

    def GetMessageTimestampSeconds(self, messageData) -> int:
        tags = messageData.tags if getattr(messageData, "tags", None) else {}
        sentTimestampMs = tags.get("tmi-sent-ts")

        if sentTimestampMs:
            try:
                return int(sentTimestampMs) // 1000
            except:
                pass

        return int(time.time())

    def GetCurrentMinuteBucket(self, timestampSeconds=None) -> int:
        if timestampSeconds is None:
            timestampSeconds = int(time.time())
        return int(timestampSeconds // 60)

    def GetSecondsUntilNextMinute(self, timestampSeconds=None) -> int:
        if timestampSeconds is None:
            timestampSeconds = int(time.time())
        currentSeconds = int(timestampSeconds)
        return 60 - (currentSeconds % 60)

    def TryConsumeMinuteQuota(self, username: str, timestampSeconds=None) -> bool:
        currentMinuteBucket = self.GetCurrentMinuteBucket(timestampSeconds)
        userCounter = self.userQueryCountsPerMinute.get(username)

        if not userCounter or userCounter["minuteBucket"] != currentMinuteBucket:
            self.userQueryCountsPerMinute[username] = {"minuteBucket": currentMinuteBucket, "count": 1}
            return True

        if userCounter["count"] >= self.maxQueriesPerMinute:
            return False

        userCounter["count"] += 1
        return True

    def FormatRemainingTime(self, remainingSeconds: int) -> str:
        if remainingSeconds < 60:
            return f"{remainingSeconds}s"

        minutes = remainingSeconds // 60
        seconds = remainingSeconds % 60
        if seconds == 0:
            return f"{minutes}m"
        return f"{minutes}m {seconds}s"

    def TryGetResponseFromFallbackModel(self, bot, messageData, isMentionedJoin) -> bool: # Returns true if the model responded, otherwise false
        try:
            response = self.geminiClient.models.generate_content(
                        model=self.fallbackModel,
                        contents="\n".join(self.messageHistory[messageData.channel]),
                        config=self.config if isMentionedJoin else self.randomJoinConfig
                    )
            reply_text = response.text.strip() if getattr(response, "text", None) else None
            if not self.IsAcceptableReply(reply_text):
                return False
            else:
                self.SendModelMessage(bot, messageData, reply_text)
                return True
        except:
            return False
            
    def __init__(self, commands):
        super().__init__(commands)
        self.geminiClient = GenAI.Client(api_key=GOOGLE_GEMINI_APIKEY)

        # support for google search and remove all safety settings
        groundingTool = types.Tool(google_search=types.GoogleSearch())
        self.config = types.GenerateContentConfig(
                                                max_output_tokens=self.maxTokens,
                                                system_instruction=self.masterPhrase,
                                                tools=[groundingTool],
                                                safety_settings=[
                                                    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                                                    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_CIVIC_INTEGRITY, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                                                    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                                                    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                                                    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HARASSMENT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                                                ])


    def HandleMessage(self, bot, messageData):
        if messageData.channel not in self.CHANNELS:
            return

        # Ignore messages from the bot itself to prevent processing its own responses
        if messageData.user.lower() == USERNAME.lower():
            return
        
        # Bot memory clear - only for authorized user and streamer
        if (messageData.user == AUTHORIZED_USER or messageData.user == messageData.channel) and messageData.content.startswith("botto restart"):
            bot.send_reply_message(messageData, "🧠🔄️👍")
            self.messageHistory[messageData.channel] = []
            return

        if messageData.channel not in self.messageHistory:
            self.messageHistory[messageData.channel] = []

        formattedHistoryContent, detectedEmoteSpans, usedCachedExternalEmotes, externalEmoteCount = self.GetFormattedHistoryContentWithDetails(messageData)
        self.LogEmoteDetectionDebug(
            messageData,
            messageData.content,
            formattedHistoryContent,
            detectedEmoteSpans,
            usedCachedExternalEmotes,
            externalEmoteCount,
        )
        self.messageHistory[messageData.channel].append(f"({messageData.user}): ({formattedHistoryContent})") # add message to message history
        if len(self.messageHistory[messageData.channel]) > self.messageHistoryLimit: # prevent message history going over the limit
            self.messageHistory[messageData.channel].pop(0)

        # bot name mentioned, trigger response
        if self.NAME_PATTERN.search(messageData.content):
            messageTimestampSeconds = self.GetMessageTimestampSeconds(messageData)

            if not self.TryConsumeMinuteQuota(messageData.user, messageTimestampSeconds):
                self.SendModelMessage(bot, messageData, f"You have exceeded your rate-limits PunOko You will be able to chat with botto in {self.FormatRemainingTime(self.GetSecondsUntilNextMinute(messageTimestampSeconds))}")
                return
            success = False

            # try to get a response maxRetries times
            for i in range(self.maxRetries):
                try:
                    response = self.geminiClient.models.generate_content(
                        model=self.currentModel,
                        contents="\n".join(self.messageHistory[messageData.channel]),
                        config=self.config
                    )
                    reply_text = response.text.strip() if getattr(response, "text", None) else None
                    if not self.IsAcceptableReply(reply_text):
                        successfulResponse = self.TryGetResponseFromFallbackModel(bot, messageData, True)
                        if not successfulResponse:
                            continue
                        else:
                            success = True
                            break

                    self.SendModelMessage(bot, messageData, reply_text)

                    # reset auto respond chance on bot mention
                    if messageData.channel in self.RANDOM_CHAT_JOIN_CHANNELS:
                        self.autoRespondChance[messageData.channel] = 0

                    success = True
                    break
                except Exception as e:
                    successfulResponse = self.TryGetResponseFromFallbackModel(bot, messageData, True)
                    if not successfulResponse:
                        continue
                    else:
                        success = True
                        break

            if not success:
                bot.send_reply_message(messageData, f"I am currently unable to respond :/")