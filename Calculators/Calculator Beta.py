import random

while True:
        f = input("4 function calc (Type 1) or Mean median mode of a list (Type 2)\n")

        
        if f == "1":       # Four function calculator
                Z = input("Input Operation (+ - * /):\n")
                if Z == ('+'):
                        A = float(input("Type First number\n"))
                        B = float(input("Type second\n"))
                        C=A+B
                        print(C)

                elif Z == ('-'):
                        A = float(input("Type First number\n"))
                        B = float(input("Type second\n"))
                        C=A-B
                        print(C)

                elif Z == ('*'):
                        A = float(input("Type First number\n"))
                        B = float(input("Type second\n"))
                        C=A*B
                        print(C)

                elif Z == ('/'):
                        A = float(input("Type First number\n"))
                        B = float(input("Type second\n"))
                        C=A/B
                        print(C)



        
        
        
        if f == "2":
                
                b=input("Do you want to type data? y/n\n")

                if b == "n":
                        print("Generating list...")
                        listofvalues = []
                        for _ in range(40):
                                listofvalues.append(random.randint(0,100))
                elif b == "y":
                        c=int(input("How many numbers in list?"))
                        listofvalues = []
                        for _ in range(c):
                                listofvalues.append(int(input("Type number\n")))
                else:
                        print("Error:\n You need to type y, or n.")
                        exit()
                        
                print(sorted(listofvalues))



                # mean calculation
                def mean(li):
                        sumVals = sum(li)
                        size = len(li)
                        if size == 0:
                                print("List too small")
                                return

                        mean = sumVals / size

                        return mean 



                def median(l):
                        li = sorted(l)

                        size = len(li)
                        if size == 0:
                                print("List too small")
                                return

                        median = 0

                        if size % 2 == 1:
                                middleindex = (size -1)  / 2
                                median = li[middleindex]
                                

                        elif size % 2 == 0:
                                middleright = li[size // 2]
                                middleleft = li[(size -1) // 2]

                                median = (middleright+middleleft) /2 
                        
                        return median


                def mode(li):
                        size = len(li)
                        if size == 0:
                                print("List too small")
                                return

                        valueoccur = {}
                        for val in li:
                                if val not in valueoccur:
                                        valueoccur [val] = 1
                                else:
                                        valueoccur [val] += 1

                        most_occurance = 0
                        current_value = 0
                        for key, value in valueoccur.items():
                                if value > most_occurance:
                                        most_occurance = value
                                        current_value = key
                                else:
                                        continue

                        # check if current best is equal to other bests
                        for key, value in valueoccur.items():
                                if value == most_occurance:
                                        print("Mode not defined")
                                        return

                        return current_value

                while True:
                        a=input("Type operation (mean, median, mode, all, or quit to stop.)\n")
                        
                        if a == "mean":
                                print(mean(listofvalues))

                        elif a == "median":
                                print(median(listofvalues))

                        elif a == "mode":
                                print(mode(listofvalues))

                        elif a == "all":
                                print("mean:", mean(listofvalues))
                                print("median:", median(listofvalues))
                                print("mode:", mode(listofvalues))

                        elif a == "quit":
                                break
                        
