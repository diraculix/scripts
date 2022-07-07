# Python Object-Oriented Programming
# class: blueprint for objects


class Employee:
    num_employees = 0
    raise_amount = 1.04  # class variables, 4% annual raise, use with self.raise_amount or Employee.raise_amount

    def __init__(self, first, last, pay):  # void, constructor, runs for every new instance (object) of the class
        self.first = first
        self.last = last
        self.pay = pay
        self.email = first.lower() + '.' + last.lower() + '@oncoray.de'
        Employee.num_employees += 1  # self statement doesn't make sense

    def display_name(self):
        fullname = f'{self.first} {self.last}'
        return fullname

    def apply_raise(self):
        self.pay = int(self.pay * self.raise_amount)

    @classmethod  # decorator
    def set_raise_amount(cls, amount):  # address class variables with 'cls', not objects themselves
        cls.raise_amount = amount
    
    @classmethod
    def from_string(cls, emp_string):
        first, last, pay = emp_string.split('-')


emp1 = Employee('Luke', 'Skywalker', 50000)

# print(emp1.display_name())
# print(Employee.display_name(emp1))  # same

print(emp1.pay)
emp1.apply_raise()
print(emp1.pay)
# print(emp1.raise_amount)  # print the class variable
# print(Employee.raise_amount)  # same 

print(emp1.__dict__)  # no raise amount in namespace, i.e. standard amount
Employee.set_raise_amount(1.07)
print(emp1.__dict__) # raise amount is part of namespace
emp1.apply_raise()
print(emp1.pay)

emp2 = Employee('Kristin', 'Stuetzer', 80000)
print(Employee.num_employees)
emp3 = Employee('Christian', 'Richter', 100000)
print(Employee.num_employees)
