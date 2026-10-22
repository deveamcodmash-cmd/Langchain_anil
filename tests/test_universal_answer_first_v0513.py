"""v0.5.13 generalized topic routing, language understanding, and response UX.

These are contract checks, not an assertion of accuracy from a live hosted LLM.
The subject set is deliberately broad to catch accidental topic-list dependence.
"""
import pytest
from app.dialogue_intelligence import general_only_question, off_topic_reminder, generic_nonanswer
from app.graph import normalize_public_reply, run_workflow
from app.schemas import ChatRequest, ConversationMessage, PlatformResource
from app.service_intelligence import is_service_request

@pytest.mark.parametrize('question', [
    'Which world is highest sex rate?',
    'Who has da most electricity production in da world',
    'Explain why electrons move',
    'Recommend a good telescope for a kid',
    'Can AI paint portraits?',
    'What is the capital of Bhutan',
    'How do I fix a squeaky bicycle?',
    'What color combinations work with teal',
    'How long does the Earth take to orbit the Sun',
    'Show me some thriller films to watch',
    'Can you explain quadratic equations',
    'Help me write a short poem about a river',
    'How can I teach my dog to sit?',
    'What is an orchestra?',
    'Who was Ada Lovelace?',
    'Why are the leaves changing colors?',
    'Which planet has the highest gravity?',
    'What does philanthropy mean?',
    'Should I water houseplants every day?',
    'What is meditation and why do people practice?',
    'Recommend me best time to have sex',
    'Is it possible for a person to live on Mars',
    'How to prepare lentil soup',
    'What is the difference between a laptop and a desktop?',
])
def test_unfamiliar_general_questions_are_not_platform_searches(question):
    assert general_only_question(question)
    assert not is_service_request(question,[PlatformResource(id=1,kind='service',title='Education Support Program')])

@pytest.mark.parametrize('question', [
    'Find education campaigns',
    'Show me five published charities on Filantrophy',
    'Donate to flood relief',
    'How much can I give?',
    'Book a yoga session',
    'Show three events',
    'List volunteering opportunities',
    'Help me create a fundraising campaign',
    'What can Filantrophy help me with?',
    'Where can I see my giving plan?',
])
def test_platform_requests_preserve_specialized_routes(question):
    assert not general_only_question(question)


def test_answer_first_then_short_platform_suggestion_once():
    question='Which planet has the highest gravity?'
    factual='Jupiter has the greatest surface gravity of the planets in our solar system.'
    first=off_topic_reminder(ChatRequest(message=question),factual)
    assert first.startswith(factual)
    assert first.lower().count('filantrophy')==1
    assert first.count('I can also help')==1
    history=[ConversationMessage(role='user',content=question),ConversationMessage(role='assistant',content=first)]
    follow=off_topic_reminder(ChatRequest(message='What about that?',history=history),'Its gravity is stronger because it is much more massive.')
    assert 'Filantrophy' not in follow


def test_general_noun_is_not_rewritten_to_company_name():
    text='Philanthropy means voluntarily helping others or supporting public good.'
    assert normalize_public_reply(text,preserve_generic_noun=True)==text
    assert 'Filantrophy' in normalize_public_reply('Philanthropy is a giving platform.')


def test_canned_brand_deflection_gets_flagged():
    assert generic_nonanswer('I can help you explore the Filantrophy information available for this topic. Which part would be most useful?')
    assert not generic_nonanswer('Some countries report higher activity, but studies differ in sampling and what counts as sexual activity.')


def test_currrent_ranking_can_be_discussed_without_claiming_live_data():
    assert general_only_question('Which country has the highest reported frequency of sexual activity?')
    assert general_only_question('Who holds the world record for endurance sports?')


def test_booking_and_giving_actions_remain_non_general():
    assert not general_only_question('Guide me booking form')
    assert not general_only_question('Remove the second campaign and reduce the budget to $9,000')
