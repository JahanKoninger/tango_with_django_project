from django.shortcuts import render
from django.urls import reverse
from rango.models import Category, Page
from rango.forms import CategoryForm, PageForm, UserForm, UserProfileForm
from django.shortcuts import redirect
from django.http import HttpResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from datetime import datetime


def get_server_side_cookie(request, cookie, default_val=None):
    val = request.session.get(cookie)
    if not val:
        val = default_val
    return val


def visitor_cookie_handler(request):
    # get the number of visits to the site
    # if the cookie doesn't exist, then 1 is used as default
    visits = int(get_server_side_cookie(request, 'visits', '1'))

    last_visit_cookie = get_server_side_cookie(request, 'last_visit', str(datetime.now()))
    last_visit_time = datetime.strptime(last_visit_cookie[:-7], '%Y-%m-%d %H:%M:%S')

    # If it's been more than a day since the last visit...
    if (datetime.now() - last_visit_time).days > 0:
        visits = visits + 1
        # Update the last visit cookie now that we have updated the count
        request.session['last_visit'] = str(datetime.now())
    else:
        # Set the last visit cookie
        request.session['last_visit'] = last_visit_cookie

    # Update/set the visits cookie
    request.session['visits'] = visits


def index(request):
    # call helper function to handle cookies
    visitor_cookie_handler(request)

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
    response = render(request, 'rango/index.html', context=context_dict)

    # return response
    return response


def about(request):
    visitor_cookie_handler(request)

    context_dict = {'name': 'Jahan Köninger', 'visits': request.session['visits']}
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


@login_required
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


@login_required
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


def register(request):
    # use boolean to keep track of whether registration is successful
    registered = False

    if request.method == 'POST':
        # get info from UserForm and UserProfileForm
        user_form = UserForm(request.POST)
        profile_form = UserProfileForm(request.POST)

        # if both forms are valid
        if user_form.is_valid() and profile_form.is_valid():
            # save user's form data to database
            user = user_form.save()

            # hash password using 'set_password' and update user object
            user.set_password(user.password)
            user.save()

            # now we need to sort out the UserProfile instance
            # we set commit=False when using .save to delay saving the model,
            # this avoids integrity problems until we're ready to save
            profile = profile_form.save(commit=False)
            profile.user = user

            # if the user provided a picture, we need to get it and include it
            if 'picture' in request.FILES:
                profile.picture = request.FILES['picture']

            # we can now save the UserProfile model instance
            profile.save()

            # update boolean to indicate that registration was successful
            registered = True
        else:
            # if invalid, print to terminal
            print(user_form.errors, profile_form.errors)
    else:
        # not a HTTP POST, so we render our form using the ModelForm instances
        # these will be blank, ready for user input
        user_form = UserForm()
        profile_form = UserProfileForm()

    # render template depending on the context
    return render(request, 'rango/register.html',
                  context = {
                      'user_form': user_form,
                      'profile_form': profile_form,
                      'registered': registered,
                  })


def user_login(request):
    # if request is http post, get relevant info
    if request.method == 'POST':
        # use request.POST.get(<variable>) instead of request.POST.get([<variable>]) as the latter throws
        # a KeyError exception if the variable does not exists. The former will simply return None
        username = request.POST.get('username')
        password = request.POST.get('password')

        # use Django built in functionality to check if username and password combination is valid
        user = authenticate(username=username, password=password)

        # if we have a user object then the details were valid
        if user:
            # make sure account is active
            if user.is_active:
                login(request, user)
                return redirect(reverse('rango:index'))
            else:
                return HttpResponse("Your Rango account is disabled.")
        else:
            # invalid login details
            print(f"Invalid login details: {username}, {password}")
            return HttpResponse("Invalid login details supplied.")
    # if not a POST request, display login form
    else:
        return render(request, 'rango/login.html')


@login_required
def restricted(request):
    return render(request, 'rango/restricted.html')


@login_required
def user_logout(request):
    # we know the user is logged in since we are using @login_required, hence we can just logout
    logout(request)
    return redirect(reverse('rango:index'))