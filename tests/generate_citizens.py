import json
from random import choice, randint, random
from string import ascii_lowercase
from datetime import datetime

n = 10000  # number of citizens
k = 1100  # ~ number of relations between them
file_name = 'citizens2.json'  # filename

towns = ["Москва", "С.Петербург", "Свинбург",
         "Алексеево", "Олександрово", "Берлин",
         "Владивосток", "Архангельск"]

alphabet = ".!,#" + ascii_lowercase + "".join(str(i) for i in range(10))
DATEFORMAT = "%d.%m.%Y"


def random_string(size):
    return "".join(choice(alphabet) for _ in range(size))


def random_date(start, end):
    start = datetime.strptime(start, DATEFORMAT)
    end = datetime.strptime(end, DATEFORMAT)
    time = start + random() * (end - start)
    return time.strftime(DATEFORMAT)


citizens = []

for citizen_id in range(1, n + 1):
    town = choice(towns)
    street = random_string(30)
    building = random_string(10)
    apartment = randint(1, 10 ** 4)
    name = '{0} {1}'.format(random_string(10).capitalize(), random_string(10).capitalize())
    birth_date = random_date('01.01.1901', '20.08.2019')
    gender = choice(['female', 'male'])
    relatives = []
    citizens.append(dict(citizen_id=citizen_id,
                         town=town,
                         street=street,
                         building=building,
                         apartment=apartment,
                         name=name,
                         birth_date=birth_date,
                         gender=gender,
                         relatives=relatives))

population = range(1, n + 1)
# generation k random relations
emitters = [choice(population) for _ in range(k)]
receivers = [choice(population) for _ in range(k)]

for emitter, receiver in zip(emitters, receivers):
    if emitter != receiver and emitter not in citizens[receiver - 1]['relatives']:
        citizens[receiver - 1]['relatives'].append(emitter)
        citizens[emitter - 1]['relatives'].append(receiver)

with open(file_name, 'w', encoding='utf8') as outfile:
    json.dump({'citizens': citizens}, outfile, ensure_ascii=False)
