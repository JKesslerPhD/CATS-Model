from cats import runopt

import argparse



if __name__ == "__main__":

    parser = argparse.ArgumentParser(prog='CATS', usage='%(prog)s [options]', description="Run the CATS model with arguments specified.")
    parser.add_argument("-t", type=str, nargs='+', help="well generate a new template of name")
    parser.add_argument("-v", action=argparse.BooleanOptionalAction, help="Will generate verbose results for each year run")
    parser.add_argument("-i", action=argparse.BooleanOptionalAction, help="Will disable autoincrementation of years")
    args = parser.parse_args()

    if args.v:
        print("Verbose output enabled")


    if args.t:

        print("Generting a new template for scenario '{}'...".format(args.t[0]))
        runopt.generate_template(args.t[0])
    else:
        runopt.run(verbose=args.v, disableautoincrement=args.i)
