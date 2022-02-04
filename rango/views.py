from django.shortcuts import render
from django.urls import reverse

from rango.models import Category, Page
from rango.forms import CategoryForm, PageForm
from django.shortcuts import redirect

def index(request):
    # Query database for the list of all categories, ordered by likes descending
    # Choose (at most) top 5
    category_list = Category.objects.order_by('-likes')[:5]
    # Query database of most viewed pages, choosing top 5
    page_list = Page.objects.order_by('-views')[:5]

    context_dict = {}
    context_dict['boldmessage'] = 'Crunchy, creamy, cookie, candy, cupcake!'
    context_dict['categories'] = category_list
    context_dict['pages'] = page_list

    # Return a rendered response to send to the client.
    # We make use of the shortcut function to make our lives easier.
    # Note that the first parameter is the template we wish to use.
    return render(request, 'rango/index.html', context=context_dict)


def about(request):
    context_dict = {'name': 'Jahan Köninger'}
    return render(request, 'rango/about.html', context=context_dict)


def show_category(request, category_name_slug):
    # create context dictionary
    context_dict = {}

    try:
        # find category with given name
        # returns DoesNotExist exception if no such category exists
        category = Category.objects.get(slug=category_name_slug)

        # retrieve pages with this category
        pages = Page.objects.filter(category=category)

        # add results list to template context dict
        context_dict['pages'] = pages
        # add category as well
        context_dict['category'] = category

    except Category.DoesNotExist:
        # if category does not exist
        context_dict['category'] = None
        context_dict['pages'] = None

    # render response and return to client
    return render(request, 'rango/category.html', context=context_dict)


def add_category(request):
    form = CategoryForm()

    # if HTTP Post received (i.e. form submitted)
    if request.method == 'POST':
        form = CategoryForm(request.POST)

        # is form valid
        if form.is_valid():
            # Save category to database
            form.save(commit=True)
            # redirect user to index view
            return redirect('/rango/')
        else:
            # if form contained errors, print them to terminal
            print(form.errors)

    # will handle bad, new or no form cases
    # render the form with error messages, if any exist
    return render(request, 'rango/add_category.html', {'form': form})


def add_page(request, category_name_slug):
    try:
        category = Category.objects.get(slug=category_name_slug)
    except Category.DoesNotExist:
        category = None

    # cannot add page to category that doesn't exist
    if category is None:
        return redirect('/rango/')

    form = PageForm()

    if request.method == 'POST':
        form = PageForm(request.POST)

        if form.is_valid():
            if category:
                page = form.save(commit=False)
                page.category = category
                page.views = 0
                page.save()

                return redirect(reverse('rango:show_category', kwargs={'category_name_slug': category_name_slug}))
        else:
            print(form.errors)

    context_dict = {'form': form, 'category': category}
    return render(request, 'rango/add_page.html', context=context_dict)
